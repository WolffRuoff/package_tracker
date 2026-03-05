"""Tests for the UPS carrier provider (scraper side)."""

from __future__ import annotations

import pytest

from scraper.carriers.base import TrackingResult
from scraper.carriers.ups import STATUS_MAPPING, UPSProvider
from scraper.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return UPSProvider()


VALID_TRACKING = "1ZABCDEF1234567890"


class TestValidateTrackingNumber:
    def test_valid_1z_format(self, provider):
        assert provider.validate_tracking_number("1Z12345E6605272234") is True

    def test_valid_uppercase(self, provider):
        assert provider.validate_tracking_number("1zabcdef1234567890") is True

    def test_invalid_no_1z_prefix(self, provider):
        assert provider.validate_tracking_number("2Z12345E6605272234") is False

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("1Z12345") is False


class TestTrackingUrl:
    def test_tracking_url(self, provider):
        url = provider.tracking_url(VALID_TRACKING)
        assert VALID_TRACKING in url
        assert "ups.com" in url


class TestParseTrackingPage:
    def test_delivered_status(self, provider, ups_delivered_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_events(self, provider, ups_delivered_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)
        assert len(result.events) == 3
        assert "Delivered" in result.events[0].description

    def test_delivered_estimated_delivery(self, provider, ups_delivered_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    def test_in_transit_status(self, provider, ups_in_transit_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_in_transit_html, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider, ups_in_transit_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_in_transit_html, result)
        assert len(result.events) == 2

    def test_not_found_stays_unknown(self, provider, ups_not_found_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_not_found_html, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, mock_browser, ups_delivered_html
    ):
        browser, mock_page = mock_browser
        mock_page.content.return_value = ups_delivered_html

        result = await provider.async_track(VALID_TRACKING, browser)

        assert result.carrier == Carrier.UPS
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 3
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_raises(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        with pytest.raises(Exception, match="Browser error"):
            await provider.async_track(VALID_TRACKING, browser)


class TestStatusMapping:
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
