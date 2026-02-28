"""Tests for the UPS carrier provider."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioresponses import aioresponses

from package_tracker.carriers.ups import (
    STATUS_MAPPING,
    UPS_TOKEN_URL,
    UPS_TRACKING_URL,
    UPSProvider,
)
from package_tracker.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return UPSProvider(client_id="test_id", client_secret="test_secret")


VALID_TRACKING = "1ZABCDEF1234567890"


class TestValidateTrackingNumber:
    """Tests for UPS tracking number validation."""

    def test_valid_1z_format(self, provider):
        assert provider.validate_tracking_number("1Z12345E6605272234") is True

    def test_valid_uppercase(self, provider):
        assert provider.validate_tracking_number("1zabcdef1234567890") is True

    def test_invalid_no_1z_prefix(self, provider):
        assert provider.validate_tracking_number("2Z12345E6605272234") is False

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("1Z12345") is False

    def test_invalid_too_long(self, provider):
        assert provider.validate_tracking_number("1Z12345E66052722341X") is False


class TestOAuthToken:
    """Tests for UPS OAuth token management."""

    @pytest.mark.asyncio
    async def test_token_acquisition(self, provider, ups_token_response):
        with aioresponses() as mocked:
            mocked.post(UPS_TOKEN_URL, payload=ups_token_response)

            await provider._ensure_token()

        assert provider._access_token == "test_token_123"
        assert provider._token_expires is not None

    @pytest.mark.asyncio
    async def test_token_reuse_when_valid(self, provider):
        provider._access_token = "existing_token"
        provider._token_expires = datetime.now() + timedelta(hours=1)

        # Should not make any HTTP call
        await provider._ensure_token()

        assert provider._access_token == "existing_token"

    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(self, provider, ups_token_response):
        provider._access_token = "old_token"
        provider._token_expires = datetime.now() - timedelta(hours=1)

        with aioresponses() as mocked:
            mocked.post(UPS_TOKEN_URL, payload=ups_token_response)

            await provider._ensure_token()

        assert provider._access_token == "test_token_123"


class TestAsyncTrack:
    """Tests for UPS async_track with mocked API."""

    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, ups_token_response, ups_json_success
    ):
        url = UPS_TRACKING_URL.format(tracking_number=VALID_TRACKING)

        with aioresponses() as mocked:
            mocked.post(UPS_TOKEN_URL, payload=ups_token_response)
            mocked.get(url, payload=ups_json_success)

            result = await provider.async_track(VALID_TRACKING)

        assert result.carrier == Carrier.UPS
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"
        assert len(result.events) == 2
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_delivery_date_parsed(
        self, provider, ups_token_response, ups_json_success
    ):
        url = UPS_TRACKING_URL.format(tracking_number=VALID_TRACKING)

        with aioresponses() as mocked:
            mocked.post(UPS_TOKEN_URL, payload=ups_token_response)
            mocked.get(url, payload=ups_json_success)

            result = await provider.async_track(VALID_TRACKING)

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.year == 2025
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    @pytest.mark.asyncio
    async def test_http_error(self, provider, ups_token_response):
        url = UPS_TRACKING_URL.format(tracking_number=VALID_TRACKING)

        with aioresponses() as mocked:
            mocked.post(UPS_TOKEN_URL, payload=ups_token_response)
            mocked.get(url, status=500)

            result = await provider.async_track(VALID_TRACKING)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestParseActivity:
    """Tests for _parse_activity."""

    def test_parses_complete_activity(self, provider):
        activity = {
            "status": {"type": "D", "description": "Delivered"},
            "location": {
                "address": {
                    "city": "Springfield",
                    "stateProvince": "IL",
                    "countryCode": "US",
                }
            },
            "date": "20250115",
            "time": "143000",
        }
        event = provider._parse_activity(activity)

        assert event is not None
        assert event.location == "Springfield, IL, US"
        assert event.description == "Delivered"
        assert event.status == TrackingStatus.DELIVERED

    def test_missing_fields(self, provider):
        activity = {"status": {"type": "I", "description": "In Transit"}}
        event = provider._parse_activity(activity)

        assert event is not None
        assert event.location == ""
        assert event.description == "In Transit"
        assert event.status == TrackingStatus.IN_TRANSIT


class TestStatusMapping:
    """Tests for UPS status mapping."""

    def test_delivered(self):
        assert STATUS_MAPPING["D"] == TrackingStatus.DELIVERED

    def test_in_transit(self):
        assert STATUS_MAPPING["I"] == TrackingStatus.IN_TRANSIT

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["O"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_pre_transit(self):
        assert STATUS_MAPPING["M"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["X"] == TrackingStatus.EXCEPTION
