"""Tests for the USPS carrier provider (scraper side)."""

from __future__ import annotations

import pytest

from scraper.carriers.base import TrackingResult
from scraper.carriers.usps import STATUS_MAPPING, USPSProvider
from scraper.const import Carrier, TrackingStatus


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

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_strips_whitespace(self, provider):
        assert provider.validate_tracking_number("  EA123456789US  ") is True


class TestTrackingUrl:
    def test_tracking_url(self, provider):
        url = provider.tracking_url("92001234567890123456")
        assert "92001234567890123456" in url
        assert "tools.usps.com" in url


class TestParseTrackingPage:
    """Tests for _parse_tracking_page with HTML fixtures."""

    def test_delivered_status(self, provider, usps_delivered_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_events(self, provider, usps_delivered_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)
        assert len(result.events) == 3
        assert result.events[0].description == "Delivered, In/At Mailbox"
        assert "Springfield" in result.events[0].location

    def test_delivered_estimated_delivery(self, provider, usps_delivered_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    def test_in_transit_status(self, provider, usps_in_transit_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider, usps_in_transit_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)
        assert len(result.events) == 2

    def test_in_transit_estimated_delivery(self, provider, usps_in_transit_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_in_transit_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 3
        assert result.estimated_delivery.day == 7
        assert result.estimated_delivery.year == 2026

    def test_not_found_stays_unknown(self, provider, usps_not_found_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_not_found_html, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    """Tests for async_track with mocked browser."""

    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, mock_browser, usps_delivered_html
    ):
        browser, mock_page = mock_browser
        mock_page.content.return_value = usps_delivered_html

        result = await provider.async_track("92001234567890123456", browser)

        assert result.carrier == Carrier.USPS
        assert result.status == TrackingStatus.DELIVERED
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_returns_unknown(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        result = await provider.async_track("92001234567890123456", browser)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestStatusMapping:
    def test_delivered(self):
        assert STATUS_MAPPING["delivered"] == TrackingStatus.DELIVERED

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["out for delivery"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self):
        assert STATUS_MAPPING["in transit"] == TrackingStatus.IN_TRANSIT

    def test_moving_through_network(self):
        assert STATUS_MAPPING["moving through network"] == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self):
        assert STATUS_MAPPING["accepted"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["alert"] == TrackingStatus.EXCEPTION


class TestParseDate:
    def test_full_date_with_year(self, provider):
        result = provider._parse_date("January 15, 2025")
        assert result is not None
        assert result.month == 1
        assert result.day == 15
        assert result.year == 2025

    def test_year_less_month_day(self, provider):
        result = provider._parse_date("March 7")
        assert result is not None
        assert result.month == 3
        assert result.day == 7

    def test_day_of_week_prefix(self, provider):
        result = provider._parse_date("Friday, March 7")
        assert result is not None
        assert result.month == 3
        assert result.day == 7

    def test_day_of_week_no_comma_with_year(self, provider):
        result = provider._parse_date("Saturday 7 March 2026")
        assert result is not None
        assert result.month == 3
        assert result.day == 7
        assert result.year == 2026

    def test_expected_delivery_by_prefix(self, provider):
        result = provider._parse_date("Expected Delivery by: Friday, March 7")
        assert result is not None
        assert result.month == 3
        assert result.day == 7

    def test_moving_through_network_status(self, provider):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(
            '<div class="track-statusbar">'
            '<div class="current-tracking-status-wrapper">'
            '<div class="tb-status">Moving Through Network</div>'
            "</div></div>",
            result,
        )
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_invalid_returns_none(self, provider):
        assert provider._parse_date("not a date at all") is None
