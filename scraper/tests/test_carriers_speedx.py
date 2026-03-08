"""Tests for the SpeedX carrier provider (scraper side)."""

from __future__ import annotations

import pytest

from scraper.carriers.base import TrackingResult
from scraper.carriers.speedx import SpeedXProvider
from scraper.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return SpeedXProvider()


class TestValidateTrackingNumber:
    def test_valid_standard(self, provider):
        assert provider.validate_tracking_number("SPXBOS039706401374") is True

    def test_valid_lowercase(self, provider):
        assert provider.validate_tracking_number("spxbos039706401374") is True

    def test_valid_strips_whitespace(self, provider):
        assert provider.validate_tracking_number("  SPXBOS039706401374  ") is True

    def test_valid_longer_hub_code(self, provider):
        assert provider.validate_tracking_number("SPXABCDE12345678") is True

    def test_invalid_missing_spx_prefix(self, provider):
        assert provider.validate_tracking_number("BOS039706401374") is False

    def test_invalid_hub_code_too_short(self, provider):
        assert provider.validate_tracking_number("SPXB039706401374") is False

    def test_invalid_hub_code_too_long(self, provider):
        assert provider.validate_tracking_number("SPXABCDEF039706401374") is False

    def test_invalid_digits_too_few(self, provider):
        assert provider.validate_tracking_number("SPXBOS1234567") is False

    def test_invalid_no_digits(self, provider):
        assert provider.validate_tracking_number("SPXBOSABC") is False


class TestTrackingUrl:
    def test_contains_tracking_number(self, provider):
        url = provider.tracking_url("spxbos039706401374")
        assert "SPXBOS039706401374" in url
        assert "tracking.speedx.io" in url

    def test_uppercases_tracking_number(self, provider):
        url = provider.tracking_url("spxbos039706401374")
        assert "spxbos039706401374" not in url


class TestParseTrackingPage:
    def test_delivered_status(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED

    def test_delivered_raw_status(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert result.raw_status == "Delivered"

    def test_delivered_events_count(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert len(result.events) == 3

    def test_delivered_first_event(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        first = result.events[0]
        assert first.status == TrackingStatus.DELIVERED
        assert "Delivered" in first.description
        assert "Malden" in first.location
        assert first.timestamp.year == 2026
        assert first.timestamp.month == 3
        assert first.timestamp.day == 4

    def test_delivered_second_event_out_for_delivery(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert result.events[1].status == TrackingStatus.OUT_FOR_DELIVERY

    def test_delivered_third_event_pre_transit(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert result.events[2].status == TrackingStatus.PRE_TRANSIT

    def test_delivered_estimated_delivery(self, provider, speedx_delivered_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page(speedx_delivered_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 3
        assert result.estimated_delivery.day == 4
        assert result.estimated_delivery.year == 2026

    def test_in_transit_status(self, provider, speedx_in_transit_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_in_transit_html, result)
        assert result.status == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit_events_count(self, provider, speedx_in_transit_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_in_transit_html, result)
        assert len(result.events) == 3

    def test_in_transit_estimated_delivery(self, provider, speedx_in_transit_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_in_transit_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 3
        assert result.estimated_delivery.day == 8
        assert result.estimated_delivery.year == 2026

    def test_order_placed_status(self, provider, speedx_order_placed_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_order_placed_html, result)
        assert result.status == TrackingStatus.PRE_TRANSIT

    def test_order_placed_events_count(self, provider, speedx_order_placed_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_order_placed_html, result)
        assert len(result.events) == 1

    def test_order_placed_no_estimated_delivery(self, provider, speedx_order_placed_html):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706647818")
        provider._parse_tracking_page(speedx_order_placed_html, result)
        assert result.estimated_delivery is None

    def test_empty_html_stays_unknown(self, provider):
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number="SPXBOS039706401374")
        provider._parse_tracking_page("<html></html>", result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestMapStatus:
    def test_delivered(self, provider):
        assert provider._map_status("LAST_MILE_DELIVERED", "Delivered") == TrackingStatus.DELIVERED

    def test_out_for_delivery(self, provider):
        assert provider._map_status("LAST_MILE_ENROUTE", "Out for Delivery") == TrackingStatus.OUT_FOR_DELIVERY

    def test_in_transit(self, provider):
        assert provider._map_status("LAST_MILE_ENROUTE", "Arrived at facility") == TrackingStatus.IN_TRANSIT

    def test_pre_transit(self, provider):
        assert provider._map_status("PICKUP", "Shipping Label Created") == TrackingStatus.PRE_TRANSIT

    def test_unknown_category(self, provider):
        assert provider._map_status("SOMETHING_ELSE", "Whatever") == TrackingStatus.UNKNOWN


class TestParseDeliveryDate:
    def test_delivered_prefix_stripped(self, provider):
        result = provider._parse_delivery_date("Delivered: March 4, 2026")
        assert result is not None
        assert result.month == 3
        assert result.day == 4
        assert result.year == 2026

    def test_plain_date(self, provider):
        result = provider._parse_delivery_date("March 4, 2026")
        assert result is not None
        assert result.month == 3
        assert result.day == 4

    def test_estimated_delivery_date_prefix_stripped(self, provider):
        result = provider._parse_delivery_date("Estimated Delivery Date: March 8, 2026")
        assert result is not None
        assert result.month == 3
        assert result.day == 8
        assert result.year == 2026

    def test_invalid_returns_none(self, provider):
        assert provider._parse_delivery_date("not a date") is None


class TestAsyncTrack:
    @pytest.mark.asyncio
    async def test_successful_tracking(self, provider, mock_browser, speedx_delivered_html):
        browser, mock_page = mock_browser
        mock_page.content.return_value = speedx_delivered_html

        result = await provider.async_track("SPXBOS039706401374", browser)

        assert result.carrier == Carrier.SPEEDX
        assert result.status == TrackingStatus.DELIVERED
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_raises(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        with pytest.raises(Exception, match="Browser error"):
            await provider.async_track("SPXBOS039706401374", browser)
