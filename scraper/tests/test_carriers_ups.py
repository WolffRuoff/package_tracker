"""Tests for the UPS carrier provider (scraper side)."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from scraper.carriers.base import STATUS_MAPPING, TrackingResult
from scraper.carriers.ups import UPSProvider
from scraper.const import Carrier, TrackingStatus


@pytest.fixture
def provider():
    return UPSProvider()


VALID_TRACKING = "1ZABCDEF1234567890"

UPS_API_JSON_DELIVERED = {
    "trackDetails": [
        {
            "errorCode": None,
            "packageStatus": "Delivered",
            "shipmentProgressActivities": [
                {
                    "date": "07/11/2026",
                    "time": "1:14 P.M.",
                    "location": "MALDEN, MA, US",
                    "activityScan": "DELIVERED",
                },
                {
                    "date": "07/11/2026",
                    "time": "9:39 A.M.",
                    "location": "Saugus, MA, United States",
                    "activityScan": "Out For Delivery Today",
                },
                {
                    "date": "07/08/2026",
                    "time": "11:33 A.M.",
                    "location": "United States",
                    "activityScan": "Shipper created a label, UPS has not received the package yet.",
                },
            ],
        }
    ]
}

UPS_API_JSON_IN_TRANSIT = {
    "trackDetails": [
        {
            "errorCode": None,
            "packageStatus": "In Transit",
            "shipmentProgressActivities": [
                {
                    "date": "07/11/2026",
                    "time": "4:25 A.M.",
                    "location": "Chelmsford, MA, United States",
                    "activityScan": "Departed from Facility",
                },
                {
                    "date": "07/08/2026",
                    "time": "11:33 A.M.",
                    "location": "United States",
                    "activityScan": "Shipper created a label, UPS has not received the package yet.",
                },
            ],
        }
    ]
}

UPS_API_JSON_NOT_FOUND = {
    "statusCode": "402",
    "statusText": "Invalid Request",
    "trackDetails": None,
}


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


class TestParseTrackingJson:
    def test_delivered_status(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_DELIVERED, result)
        assert result.status == TrackingStatus.DELIVERED
        assert result.raw_status == "Delivered"

    def test_delivered_events(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_DELIVERED, result)
        assert len(result.events) == 3
        assert result.events[0].description == "DELIVERED"
        assert result.events[0].location == "MALDEN, MA, US"
        assert result.events[0].status == TrackingStatus.DELIVERED

    def test_delivered_estimated_delivery(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_DELIVERED, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 7
        assert result.estimated_delivery.day == 11
        assert result.estimated_delivery.year == 2026

    def test_in_transit_status(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_IN_TRANSIT, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_in_transit_events(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_IN_TRANSIT, result)
        assert len(result.events) == 2
        assert result.events[0].description == "Departed from Facility"

    def test_not_found_stays_unknown(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json(UPS_API_JSON_NOT_FOUND, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []

    def test_missing_key(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_json({}, result)
        assert result.status == TrackingStatus.UNKNOWN

    def test_error_code_present(self, provider):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        data = {"trackDetails": [{"errorCode": "10001", "packageStatus": "Delivered"}]}
        provider._parse_tracking_json(data, result)
        assert result.status == TrackingStatus.UNKNOWN


class TestParseTrackingPage:
    """Covers the DOM fallback path used when the GetStatus API call is missed."""

    def test_delivered_status(self, provider, ups_delivered_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)
        assert result.status == TrackingStatus.DELIVERED
        assert "delivered" in result.raw_status.lower()

    def test_delivered_estimated_delivery(self, provider, ups_delivered_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_delivered_html, result)
        assert result.estimated_delivery is not None
        assert result.estimated_delivery.month == 7
        assert result.estimated_delivery.day == 11

    def test_in_transit_status(self, provider, ups_in_transit_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_in_transit_html, result)
        assert result.status == TrackingStatus.IN_TRANSIT

    def test_not_found_stays_unknown(self, provider, ups_not_found_html):
        result = TrackingResult(carrier=Carrier.UPS, tracking_number="TEST")
        provider._parse_tracking_page(ups_not_found_html, result)
        assert result.status == TrackingStatus.UNKNOWN
        assert result.events == []


class TestAsyncTrack:
    @pytest.mark.asyncio
    async def test_json_path(self, provider, mock_browser):
        """When the GetStatus API response is intercepted, it's used over the DOM."""
        browser, mock_page = mock_browser

        captured_callbacks: list = []
        mock_page.on = MagicMock(
            side_effect=lambda event, cb: captured_callbacks.append(cb)
            if event == "response"
            else None
        )

        mock_response = AsyncMock()
        mock_response.url = "https://webapis.ups.com/track/api/Track/GetStatus?loc=en_US"
        mock_response.json = AsyncMock(return_value=UPS_API_JSON_DELIVERED)

        async def goto_side_effect(url, **kwargs):
            if captured_callbacks:
                await captured_callbacks[0](mock_response)

        mock_page.goto.side_effect = goto_side_effect

        result = await provider.async_track(VALID_TRACKING, browser)

        assert result.carrier == Carrier.UPS
        assert result.status == TrackingStatus.DELIVERED
        assert len(result.events) == 3
        assert result.last_updated is not None
        mock_page.wait_for_selector.assert_not_called()

    @pytest.mark.asyncio
    async def test_html_fallback_when_no_api_response(
        self, provider, mock_browser, ups_delivered_html, monkeypatch
    ):
        """When no API response is intercepted, falls back to HTML parsing."""
        monkeypatch.setattr("scraper.carriers.ups._GETSTATUS_TIMEOUT", 0.01)
        browser, mock_page = mock_browser
        mock_page.content.return_value = ups_delivered_html

        result = await provider.async_track(VALID_TRACKING, browser)

        mock_page.wait_for_selector.assert_called_once()
        assert result.carrier == Carrier.UPS
        assert result.status == TrackingStatus.DELIVERED
        assert result.last_updated is not None

    @pytest.mark.asyncio
    async def test_browser_error_raises(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.goto.side_effect = Exception("Browser error")

        with pytest.raises(Exception, match="Browser error"):
            await provider.async_track(VALID_TRACKING, browser)

    @pytest.mark.asyncio
    async def test_logs_diagnostics_when_both_api_and_dom_fail(
        self, provider, mock_browser, caplog, monkeypatch
    ):
        """Neither the API response nor the DOM fallback selector show up."""
        monkeypatch.setattr("scraper.carriers.ups._GETSTATUS_TIMEOUT", 0.01)
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("Timeout exceeded")
        mock_page.content.return_value = "<html>stuck</html>"

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception, match="Timeout exceeded"):
                await provider.async_track(VALID_TRACKING, browser)

        assert "Page load failed" in caplog.text


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
