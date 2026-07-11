"""Tests for the USPS carrier provider (scraper side)."""

from __future__ import annotations

from datetime import timedelta, timezone

import pytest

from scraper.carriers.base import STATUS_MAPPING, TrackingResult
from scraper.carriers.usps import USPSProvider
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

    def test_estimated_delivery_stays_naive(self, provider, usps_delivered_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_delivered_html, result)
        # ETA is a carrier calendar date with no real timezone; it must stay
        # naive so it isn't shifted a day when localized for display.
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.tzinfo is None

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


class TestParseV2ProgressBarLayout:
    """Tests for the v2 USPS progress-bar page layout (no .track-statusbar)."""

    def test_in_transit_status_from_container_class(
        self, provider, usps_v2_in_transit_html
    ):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_in_transit_html, result)
        assert result.status == TrackingStatus.IN_TRANSIT
        assert result.raw_status == "On the Way"

    def test_in_transit_events(self, provider, usps_v2_in_transit_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_in_transit_html, result)
        # Two real steps; the greyed-out "upcoming-step" placeholders are excluded.
        assert len(result.events) == 2
        assert result.events[0].description == "Arrived at USPS Facility"
        assert "ANAHEIM" in result.events[0].location

    def test_in_transit_event_date_with_time(
        self, provider, usps_v2_in_transit_html
    ):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_in_transit_html, result)
        # "July 8, 2026 9:49 AM" -> the clock time is stripped before parsing.
        assert result.events[0].timestamp.month == 7
        assert result.events[0].timestamp.day == 8
        assert result.events[0].timestamp.year == 2026

    def test_in_transit_estimated_delivery_monday(
        self, provider, usps_v2_in_transit_html
    ):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_in_transit_html, result)
        # Regression: "Monday" must not have its "on" stripped by the date cleaner.
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 7
        assert result.estimated_delivery.day == 13
        assert result.estimated_delivery.year == 2026

    def test_delivered_status_from_container_class(
        self, provider, usps_v2_delivered_html
    ):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"

    def test_delivered_events(self, provider, usps_v2_delivered_html):
        result = TrackingResult(carrier=Carrier.USPS, tracking_number="TEST")
        provider._parse_tracking_page(usps_v2_delivered_html, result)
        assert len(result.events) == 3
        assert result.events[0].description == "Delivered, In/At Mailbox"


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
    async def test_last_updated_is_utc_aware(
        self, provider, mock_browser, usps_delivered_html
    ):
        browser, mock_page = mock_browser
        mock_page.content.return_value = usps_delivered_html

        result = await provider.async_track("92001234567890123456", browser)

        # last_updated is an instant we stamp — it must be timezone-aware UTC so
        # the frontend renders "Updated:" in the viewer's local time.
        assert result.last_updated.tzinfo is not None
        assert result.last_updated.utcoffset() == timedelta(0)

    @pytest.mark.asyncio
    async def test_browser_error_raises(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        with pytest.raises(Exception, match="Browser error"):
            await provider.async_track("92001234567890123456", browser)


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

    def test_date_with_trailing_time(self, provider):
        result = provider._parse_date("July 8, 2026 9:49 AM")
        assert result is not None
        assert result.month == 7
        assert result.day == 8
        assert result.year == 2026

    def test_monday_not_corrupted_by_on_stripping(self, provider):
        result = provider._parse_date("Monday 13 July 2026")
        assert result is not None
        assert result.month == 7
        assert result.day == 13
        assert result.year == 2026

    def test_invalid_returns_none(self, provider):
        assert provider._parse_date("not a date at all") is None
