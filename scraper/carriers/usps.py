"""USPS carrier provider using web scraping."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

USPS_TRACKING_PAGE = (
    "https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
)

WAIT_SELECTOR = ".delivery-status-container, .tracking-progress, .error-message"

STATUS_MAPPING: dict[str, TrackingStatus] = {
    "delivered": TrackingStatus.DELIVERED,
    "out for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "in transit": TrackingStatus.IN_TRANSIT,
    "accepted": TrackingStatus.PRE_TRANSIT,
    "pre-shipment": TrackingStatus.PRE_TRANSIT,
    "shipping label created": TrackingStatus.PRE_TRANSIT,
    "alert": TrackingStatus.EXCEPTION,
    "notice left": TrackingStatus.EXCEPTION,
    "delivery attempt": TrackingStatus.EXCEPTION,
}


class USPSProvider(CarrierProvider):
    """USPS tracking provider via web scraping."""

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.USPS

    @property
    def name(self) -> str:
        return "USPS"

    def tracking_url(self, tracking_number: str) -> str:
        return USPS_TRACKING_PAGE.format(tracking_number=tracking_number)

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate USPS tracking number format."""
        tn = tracking_number.strip().upper()
        if re.match(r"^\d{20,22}$", tn):
            return True
        if re.match(r"^[A-Z]{2}\d{9}US$", tn):
            return True
        return False

    async def async_track(
        self, tracking_number: str, browser: Browser
    ) -> TrackingResult:
        """Track a USPS package by scraping the tracking page."""
        result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number=tracking_number,
        )

        try:
            url = self.tracking_url(tracking_number)
            html = await self._get_page_content(browser, url, WAIT_SELECTOR)
            self._parse_tracking_page(html, result)
            result.last_updated = datetime.now()
        except Exception:
            _LOGGER.exception("Error tracking USPS package %s", tracking_number)

        return result

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        """Parse the USPS tracking page HTML."""
        soup = BeautifulSoup(html, "html.parser")

        status_banner = soup.select_one(
            ".delivery-status-container .tb-status, "
            ".tracking-progress .tb-status"
        )
        if status_banner:
            raw_status = status_banner.get_text(strip=True)
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        eta_el = soup.select_one(".expected-delivery-date")
        if eta_el:
            eta_text = eta_el.get_text(strip=True)
            result.estimated_delivery = self._parse_date(eta_text)

        history_rows = soup.select(
            ".track-bar-container .tb-step, "
            "#trackingHistory_list .tb-step"
        )
        for row in history_rows:
            event = self._parse_event_row(row)
            if event:
                result.events.append(event)

    def _map_status(self, raw_status: str) -> TrackingStatus:
        """Map a raw status string to TrackingStatus."""
        lower = raw_status.lower()
        for key, status in STATUS_MAPPING.items():
            if key in lower:
                return status
        return TrackingStatus.UNKNOWN

    def _parse_date(self, text: str) -> datetime | None:
        """Try to parse a date from text like 'January 15, 2025'."""
        formats = [
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
        ]
        cleaned = re.sub(r"(Expected Delivery|by|on)\s*:?\s*", "", text).strip()
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None

    def _parse_event_row(self, row) -> TrackingEvent | None:
        """Parse a single tracking event row from the history."""
        desc_el = row.select_one(".tb-status-detail, .tb-status")
        date_el = row.select_one(".tb-date, .tb-date-time")
        loc_el = row.select_one(".tb-location")

        description = desc_el.get_text(strip=True) if desc_el else ""
        location = loc_el.get_text(strip=True) if loc_el else ""

        timestamp = datetime.now()
        if date_el:
            date_text = date_el.get_text(strip=True)
            parsed = self._parse_date(date_text)
            if parsed:
                timestamp = parsed

        status = self._map_status(description)

        return TrackingEvent(
            timestamp=timestamp,
            location=location,
            description=description,
            status=status,
        )
