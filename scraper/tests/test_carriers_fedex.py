"""Tests for the FedEx carrier provider (scraper side)."""

from __future__ import annotations

import pytest

from scraper.carriers.base import TrackingResult
from scraper.carriers.fedex import DESCRIPTION_MAPPING, STATUS_MAPPING, FedExProvider
from scraper.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return FedExProvider()


VALID_TRACKING_12 = "123456789012"


class TestValidateTrackingNumber:
    def test_valid_12_digit(self, provider):
        assert provider.validate_tracking_number("123456789012") is True

    def test_valid_15_digit(self, provider):
        assert provider.validate_tracking_number("123456789012345") is True

    def test_valid_96_prefix(self, provider):
        assert provider.validate_tracking_number("96123456789012345678") is True

    def test_valid_dt_prefix(self, provider):
        assert provider.validate_tracking_number("DT123456789012") is True

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_invalid_1z_prefix(self, provider):
        assert provider.validate_tracking_number("1Z12345E6605272234") is False


class TestTrackingUrl:
    def test_tracking_url(self, provider):
        url = provider.tracking_url(VALID_TRACKING_12)
        assert VALID_TRACKING_12 in url
        assert "fedex.com" in url


class TestParseTrackingPage:
    def test_delivered_status(self, provider, fedex_delivered_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_events(self, provider, fedex_delivered_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_delivered_html, result)
        assert len(result.events) == 3
        assert "Delivered" in result.events[0].description

    def test_delivered_estimated_delivery(self, provider, fedex_delivered_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_delivered_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15

    def test_in_transit_status(self, provider, fedex_in_transit_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_in_transit_html, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider, fedex_in_transit_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_in_transit_html, result)
        assert len(result.events) == 2

    def test_not_found_stays_unknown(self, provider, fedex_not_found_html):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_page(fedex_not_found_html, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    @pytest.mark.asyncio
    async def test_successful_tracking(
        self, provider, mock_browser, fedex_delivered_html
    ):
        browser, mock_page = mock_browser
        mock_page.content.return_value = fedex_delivered_html

        result = await provider.async_track(VALID_TRACKING_12, browser)

        assert result.carrier == Carrier.FEDEX
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 3
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_returns_unknown(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        result = await provider.async_track(VALID_TRACKING_12, browser)

        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestStatusMapping:
    def test_delivered(self):
        assert STATUS_MAPPING["delivered"] == TrackingStatus.DELIVERED

    def test_out_for_delivery(self):
        assert STATUS_MAPPING["out for delivery"] == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self):
        assert STATUS_MAPPING["in transit"] == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self):
        assert STATUS_MAPPING["picked up"] == TrackingStatus.PRE_TRANSIT

    def test_exception(self):
        assert STATUS_MAPPING["delivery exception"] == TrackingStatus.EXCEPTION

    def test_description_delivered(self):
        assert DESCRIPTION_MAPPING["Delivered"] == TrackingStatus.DELIVERED

    def test_description_in_transit(self):
        assert DESCRIPTION_MAPPING["In transit"] == TrackingStatus.IN_TRANSIT
