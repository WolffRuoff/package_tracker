"""Tests for the UPS carrier provider."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from package_tracker.carriers.ups import STATUS_MAPPING, UPSProvider
from package_tracker.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return UPSProvider()


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


class TestTrackingUrl:
    """Tests for tracking URL generation."""

    def test_tracking_url(self, provider):
        url = provider.tracking_url(VALID_TRACKING)
        assert VALID_TRACKING in url
        assert "ups.com" in url


class TestParseTrackingPage:
    """Tests for _parse_tracking_page with HTML fixtures."""

    def test_delivered_status(self, provider, ups_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)

        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_events(self, provider, ups_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)

        assert len(result.events) == 3
        assert "Delivered" in result.events[0].description

    def test_delivered_estimated_delivery(self, provider, ups_delivered_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)

        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    def test_in_transit_status(self, provider, ups_in_transit_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_in_transit_html, result)

        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider, ups_in_transit_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_in_transit_html, result)

        assert len(result.events) == 2

    def test_not_found_stays_unknown(self, provider, ups_not_found_html):
        from package_tracker.carriers.base import TrackingResult

        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_not_found_html, result)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    """Tests for async_track with mocked Playwright."""

    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, mock_playwright, ups_delivered_html
    ):
        mock_cm, mock_page = mock_playwright
        mock_page.content.return_value = ups_delivered_html

        with patch(
            "package_tracker.carriers.base.async_playwright", return_value=mock_cm
        ):
            result = await provider.async_track(VALID_TRACKING)

        assert result.carrier == Carrier.UPS
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 3
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_playwright_error_returns_unknown(self, provider, mock_playwright):
        mock_cm, mock_page = mock_playwright
        mock_page.goto.side_effect = Exception("Browser error")

        with patch(
            "package_tracker.carriers.base.async_playwright", return_value=mock_cm
        ):
            result = await provider.async_track(VALID_TRACKING)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestStatusMapping:
    """Tests for UPS status mapping."""

    def test_delivered(self):
        assert STATUS_MAPPING["delivered"] == TrackingStatus.DELIVERED

    def test_in_transit(self):
        assert STATUS_MAPPING["in transit"] == TrackingStatus.IN_TRANSIT

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["out for delivery"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_pre_transit(self):
        assert STATUS_MAPPING["order processed"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["exception"] == TrackingStatus.EXCEPTION
