"""Tests for the USPS carrier provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from package_tracker.carriers.usps import STATUS_MAPPING, USPSProvider
from package_tracker.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return USPSProvider()


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


class TestTrackingUrl:
    """Tests for tracking URL generation."""

    def test_tracking_url(self, provider):
        url = provider.tracking_url("92001234567890123456")
        assert "92001234567890123456" in url
        assert "tools.usps.com" in url


class TestParseTrackingPage:
    """Tests for _parse_tracking_page with HTML fixtures."""

    def test_delivered_status(self, provider, usps_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)

        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_events(self, provider, usps_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)

        assert len(result.events) == 3
        assert result.events[0].description == "Delivered, In/At Mailbox"
        assert "Springfield" in result.events[0].location

    def test_delivered_estimated_delivery(self, provider, usps_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    def test_in_transit_status(self, provider, usps_in_transit_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)

        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider, usps_in_transit_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)

        assert len(result.events) == 2

    def test_in_transit_estimated_delivery(self, provider, usps_in_transit_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 16

    def test_not_found_stays_unknown(self, provider, usps_not_found_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_not_found_html, result)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    """Tests for async_track with mocked Playwright."""

    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, mock_playwright, usps_delivered_html
    ):
        mock_cm, mock_page = mock_playwright
        mock_page.content.return_value = usps_delivered_html

        with patch(
            "package_tracker.carriers.base.async_playwright", return_value=mock_cm
        ):
            result = await provider.async_track("92001234567890123456")

        assert result.carrier == Carrier.USPS
        assert result.status == TrackingStatus.DELIVERED
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_playwright_error_returns_unknown(self, provider, mock_playwright):
        mock_cm, mock_page = mock_playwright
        mock_page.goto.side_effect = Exception("Browser error")

        with patch(
            "package_tracker.carriers.base.async_playwright", return_value=mock_cm
        ):
            result = await provider.async_track("92001234567890123456")

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestStatusMapping:
    """Tests for USPS status mapping."""

    def test_delivered(self):
        assert STATUS_MAPPING["delivered"] == TrackingStatus.DELIVERED

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["out for delivery"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self):
        assert STATUS_MAPPING["in transit"] == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self):
        assert STATUS_MAPPING["accepted"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["alert"] == TrackingStatus.EXCEPTION

    def test_unknown_status_defaults(self):
        assert (
            STATUS_MAPPING.get("SomethingRandom", TrackingStatus.UNKNOWN)
            == TrackingStatus.UNKNOWN
        )
