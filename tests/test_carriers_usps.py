"""Tests for the USPS carrier provider."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioresponses import aioresponses

from package_tracker.carriers.usps import STATUS_MAPPING, USPS_TRACKING_URL, USPSProvider
from package_tracker.const import Carrier, TrackingStatus

USPS_URL_PATTERN = re.compile(r"^https://secure\.shippingapis\.com/ShippingAPI\.dll.*")


@pytest.fixture
def provider():
    return USPSProvider(api_key="test_user_id")


class TestValidateTrackingNumber:
    """Tests for USPS tracking number validation."""

    def test_valid_20_digit(self, provider):
        assert provider.validate_tracking_number("92001234567890123456") is True

    def test_valid_22_digit(self, provider):
        assert provider.validate_tracking_number("9200123456789012345678") is True

    def test_valid_service_prefix(self, provider):
        assert provider.validate_tracking_number("EA123456789US") is True

    def test_valid_service_prefix_ec(self, provider):
        assert provider.validate_tracking_number("EC123456789US") is True

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_invalid_letters_in_numeric(self, provider):
        assert provider.validate_tracking_number("9200ABCD567890123456") is False

    def test_invalid_service_prefix_wrong_country(self, provider):
        assert provider.validate_tracking_number("EA123456789UK") is False

    def test_strips_whitespace(self, provider):
        assert provider.validate_tracking_number("  EA123456789US  ") is True


class TestAsyncTrack:
    """Tests for USPS async_track with mocked API."""

    @pytest.mark.asyncio
    async def test_successful_tracking(self, provider, usps_xml_success):
        with aioresponses() as mocked:
            mocked.get(USPS_URL_PATTERN, body=usps_xml_success)

            result = await provider.async_track("92001234567890123456")

        assert result.carrier == Carrier.USPS
        assert result.tracking_number == "92001234567890123456"
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"
        assert len(result.events) == 3  # summary + 2 details
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_estimated_delivery_parsed(self, provider, usps_xml_success):
        with aioresponses() as mocked:
            mocked.get(USPS_URL_PATTERN, body=usps_xml_success)

            result = await provider.async_track("92001234567890123456")

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    @pytest.mark.asyncio
    async def test_error_in_xml(self, provider, usps_xml_error):
        with aioresponses() as mocked:
            mocked.get(USPS_URL_PATTERN, body=usps_xml_error)

            result = await provider.async_track("INVALID")

        assert result.status == TrackingStatus.UNKNOWN
        assert "valid tracking number" in result.raw_status.lower()

    @pytest.mark.asyncio
    async def test_http_error(self, provider):
        with aioresponses() as mocked:
            mocked.get(USPS_URL_PATTERN, status=500)

            result = await provider.async_track("92001234567890123456")

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []

    @pytest.mark.asyncio
    async def test_malformed_xml(self, provider):
        with aioresponses() as mocked:
            mocked.get(USPS_URL_PATTERN, body="<not>valid xml")

            result = await provider.async_track("92001234567890123456")

        # Should not raise, returns default result
        assert result.carrier == Carrier.USPS


class TestParseEvent:
    """Tests for _parse_event."""

    def test_parses_location(self, provider):
        from xml.etree import ElementTree

        xml = """<TrackSummary>
            <Event>Delivered</Event>
            <EventDate>January 15, 2025</EventDate>
            <EventTime>2:30 pm</EventTime>
            <EventCity>Springfield</EventCity>
            <EventState>IL</EventState>
        </TrackSummary>"""
        element = ElementTree.fromstring(xml)
        event = provider._parse_event(element)

        assert event is not None
        assert event.location == "Springfield, IL"
        assert event.description == "Delivered"
        assert event.status == TrackingStatus.DELIVERED

    def test_missing_fields(self, provider):
        from xml.etree import ElementTree

        xml = "<TrackDetail><Event>In Transit</Event></TrackDetail>"
        element = ElementTree.fromstring(xml)
        event = provider._parse_event(element)

        assert event is not None
        assert event.location == ""
        assert event.description == "In Transit"


class TestStatusMapping:
    """Tests for USPS status mapping."""

    def test_delivered(self):
        assert STATUS_MAPPING["Delivered"] == TrackingStatus.DELIVERED

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["Out for Delivery"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self):
        assert STATUS_MAPPING["In Transit"] == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self):
        assert STATUS_MAPPING["Shipping Label Created"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["Alert"] == TrackingStatus.EXCEPTION

    def test_unknown_status_defaults(self):
        assert STATUS_MAPPING.get("SomethingRandom", TrackingStatus.UNKNOWN) == TrackingStatus.UNKNOWN
