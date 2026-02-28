"""Tests for the FedEx carrier provider."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from aioresponses import aioresponses

from package_tracker.carriers.fedex import (
    DESCRIPTION_MAPPING,
    FEDEX_TOKEN_URL,
    FEDEX_TRACK_URL,
    STATUS_MAPPING,
    FedExProvider,
)
from package_tracker.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return FedExProvider(api_key="test_key", secret_key="test_secret")


VALID_TRACKING_12 = "123456789012"
VALID_TRACKING_15 = "123456789012345"


class TestValidateTrackingNumber:
    """Tests for FedEx tracking number validation."""

    def test_valid_12_digit(self, provider):
        assert provider.validate_tracking_number("123456789012") is True

    def test_valid_15_digit(self, provider):
        assert provider.validate_tracking_number("123456789012345") is True

    def test_valid_96_prefix(self, provider):
        assert provider.validate_tracking_number("96123456789012345678") is True

    def test_valid_dt_prefix(self, provider):
        assert provider.validate_tracking_number("DT123456789012") is True

    def test_valid_dt_case_insensitive(self, provider):
        assert provider.validate_tracking_number("dt123456789012") is True

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_invalid_letters(self, provider):
        assert provider.validate_tracking_number("12345ABCDE12") is False

    def test_invalid_1z_prefix(self, provider):
        """Should not match UPS-style tracking numbers."""
        assert provider.validate_tracking_number("1Z12345E6605272234") is False


class TestOAuthToken:
    """Tests for FedEx OAuth token management."""

    @pytest.mark.asyncio
    async def test_token_acquisition(self, provider, fedex_token_response):
        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)

            await provider._ensure_token()

        assert provider._access_token == "fedex_token_123"
        assert provider._token_expires is not None

    @pytest.mark.asyncio
    async def test_token_reuse_when_valid(self, provider):
        provider._access_token = "existing_token"
        provider._token_expires = datetime.now() + timedelta(hours=1)

        await provider._ensure_token()

        assert provider._access_token == "existing_token"

    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(self, provider, fedex_token_response):
        provider._access_token = "old_token"
        provider._token_expires = datetime.now() - timedelta(hours=1)

        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)

            await provider._ensure_token()

        assert provider._access_token == "fedex_token_123"


class TestAsyncTrack:
    """Tests for FedEx async_track with mocked API."""

    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, fedex_token_response, fedex_json_success
    ):
        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)
            mocked.post(FEDEX_TRACK_URL, payload=fedex_json_success)

            result = await provider.async_track(VALID_TRACKING_12)

        assert result.carrier == Carrier.FEDEX
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"
        assert len(result.events) == 2
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_estimated_delivery_parsed(
        self, provider, fedex_token_response, fedex_json_success
    ):
        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)
            mocked.post(FEDEX_TRACK_URL, payload=fedex_json_success)

            result = await provider.async_track(VALID_TRACKING_12)

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.year == 2025
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    @pytest.mark.asyncio
    async def test_error_in_response(self, provider, fedex_token_response):
        error_response = {
            "output": {
                "completeTrackResults": [
                    {
                        "trackResults": [
                            {
                                "error": {
                                    "code": "TRACKING.TRACKINGNUMBER.NOTFOUND",
                                    "message": "Tracking number not found",
                                }
                            }
                        ]
                    }
                ]
            }
        }

        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)
            mocked.post(FEDEX_TRACK_URL, payload=error_response)

            result = await provider.async_track(VALID_TRACKING_12)

        assert result.raw_status == "Tracking number not found"
        assert result.status == TrackingStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_http_error(self, provider, fedex_token_response):
        with aioresponses() as mocked:
            mocked.post(FEDEX_TOKEN_URL, payload=fedex_token_response)
            mocked.post(FEDEX_TRACK_URL, status=500)

            result = await provider.async_track(VALID_TRACKING_12)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestParseScan:
    """Tests for _parse_scan."""

    def test_parses_complete_scan(self, provider):
        scan = {
            "eventDescription": "Delivered",
            "derivedStatusCode": "DL",
            "scanLocation": {
                "city": "Springfield",
                "stateOrProvinceCode": "IL",
                "countryCode": "US",
            },
            "date": "2025-01-15T14:30:00Z",
        }
        event = provider._parse_scan(scan)

        assert event is not None
        assert event.location == "Springfield, IL, US"
        assert event.description == "Delivered"
        assert event.status == TrackingStatus.DELIVERED

    def test_fallback_to_description_mapping(self, provider):
        scan = {
            "eventDescription": "In transit",
            "eventType": "UNKNOWN_CODE",
            "scanLocation": {},
            "date": "2025-01-14T08:00:00Z",
        }
        event = provider._parse_scan(scan)

        assert event is not None
        assert event.status == TrackingStatus.IN_TRANSIT

    def test_missing_location(self, provider):
        scan = {
            "eventDescription": "Picked Up",
            "derivedStatusCode": "PU",
        }
        event = provider._parse_scan(scan)

        assert event is not None
        assert event.location == ""


class TestStatusMapping:
    """Tests for FedEx status mappings."""

    def test_delivered(self):
        assert STATUS_MAPPING["DL"] == TrackingStatus.DELIVERED

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["OD"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self):
        assert STATUS_MAPPING["IT"] == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self):
        assert STATUS_MAPPING["PU"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["DE"] == TrackingStatus.EXCEPTION

    def test_description_delivered(self):
        assert DESCRIPTION_MAPPING["Delivered"] == TrackingStatus.DELIVERED

    def test_description_in_transit(self):
        assert DESCRIPTION_MAPPING["In transit"] == TrackingStatus.IN_TRANSIT
