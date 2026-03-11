"""Tests for the FedEx carrier provider (scraper side)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from scraper.carriers.base import TrackingResult
from scraper.carriers.fedex import DESCRIPTION_MAPPING, STATUS_MAPPING, FedExProvider
from scraper.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return FedExProvider()


VALID_TRACKING_12 = "123456789012"

FEDEX_API_JSON_DELIVERED = {
    "output": {
        "packages": [
            {
                "mainStatus": "Delivered",
                "estDeliveryDt": "2025-01-15T00:00:00+00:00",
                "scanEventList": [
                    {
                        "date": "2025-01-15",
                        "time": "10:00:00",
                        "status": "Delivered",
                        "scanLocation": "Springfield, IL 62701 US",
                    },
                    {
                        "date": "2025-01-15",
                        "time": "06:00:00",
                        "status": "On FedEx vehicle for delivery",
                        "scanLocation": "Springfield, IL 62701 US",
                    },
                ],
            }
        ]
    }
}

FEDEX_API_JSON_IN_TRANSIT = {
    "output": {
        "packages": [
            {
                "mainStatus": "In transit",
                "estDeliveryDt": "2025-01-16T00:00:00+00:00",
                "scanEventList": [
                    {
                        "date": "2025-01-14",
                        "time": "14:30:00",
                        "status": "Departed FedEx location",
                        "scanLocation": "Memphis, TN 38118 US",
                    }
                ],
            }
        ]
    }
}


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


class TestParseTrackingJson:
    def test_delivered_status(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json(FEDEX_API_JSON_DELIVERED, result)
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"

    def test_delivered_estimated_delivery(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json(FEDEX_API_JSON_DELIVERED, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 1
        assert result.estimated_delivery.day == 15
        assert result.estimated_delivery.year == 2025

    def test_delivered_events(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json(FEDEX_API_JSON_DELIVERED, result)
        assert len(result.events) == 2
        assert result.events[0].description == "Delivered"
        assert result.events[0].location == "Springfield, IL 62701 US"
        assert result.events[0].status == TrackingStatus.DELIVERED

    def test_in_transit_status(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json(FEDEX_API_JSON_IN_TRANSIT, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json(FEDEX_API_JSON_IN_TRANSIT, result)
        assert len(result.events) == 1
        assert result.events[0].description == "Departed FedEx location"

    def test_empty_package_list(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        data = {"output": {"packages": []}}
        provider._parse_tracking_json(data, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []

    def test_missing_key(self, provider):
        result = TrackingResult(carrier=Carrier.FEDEX, tracking_number="TEST")
        provider._parse_tracking_json({}, result)
        assert result.status == TrackingStatus.UNKNOWN


class TestAsyncTrack:
    @pytest.mark.asyncio
    async def test_json_path_two_goto_calls(self, provider, mock_browser):
        """When API response is intercepted, result is populated via JSON path."""
        browser, mock_page = mock_browser

        captured_callbacks: list = []
        mock_page.on = MagicMock(
            side_effect=lambda event, cb: captured_callbacks.append(cb)
            if event == "response"
            else None
        )

        mock_response = AsyncMock()
        mock_response.url = "https://www.fedex.com/trackingCal/track"
        mock_response.json = AsyncMock(return_value=FEDEX_API_JSON_DELIVERED)

        call_count = 0

        async def goto_side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2 and captured_callbacks:
                await captured_callbacks[0](mock_response)

        mock_page.goto.side_effect = goto_side_effect

        result = await provider.async_track(VALID_TRACKING_12, browser)

        assert mock_page.goto.call_count == 2
        # First call = homepage warm-up
        first_url = mock_page.goto.call_args_list[0].args[0]
        assert "home" in first_url
        # Second call = tracking URL
        second_url = mock_page.goto.call_args_list[1].args[0]
        assert VALID_TRACKING_12 in second_url

        assert result.carrier == Carrier.FEDEX
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 2
        assert result.last_updated is not None
        # wait_for_selector should NOT be called in the JSON path
        mock_page.wait_for_selector.assert_not_called()

    @pytest.mark.asyncio
    async def test_html_fallback_when_no_api_response(
        self, provider, mock_browser, fedex_delivered_html
    ):
        """When no API response is intercepted, falls back to HTML parsing."""
        browser, mock_page = mock_browser
        mock_page.content.return_value = fedex_delivered_html

        result = await provider.async_track(VALID_TRACKING_12, browser)

        assert mock_page.goto.call_count == 2
        mock_page.wait_for_selector.assert_called_once()
        assert result.carrier == Carrier.FEDEX
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 3
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_raises(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        with pytest.raises(Exception, match="Browser error"):
            await provider.async_track(VALID_TRACKING_12, browser)


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
