"""FedEx carrier provider using web scraping."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

FEDEX_TRACKING_PAGE = "https://www.fedex.com/fedextrack/?trknbr={tracking_number}"

WAIT_SELECTOR = (
    ".shipment-status-progress, "
    ".tracking-result, "
    ".alert__heading"
)

STATUS_MAPPING: dict[str, TrackingStatus] = {
    "delivered": TrackingStatus.DELIVERED,
    "out for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "on fedex vehicle for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "in transit": TrackingStatus.IN_TRANSIT,
    "at local fedex facility": TrackingStatus.IN_TRANSIT,
    "departed fedex location": TrackingStatus.IN_TRANSIT,
    "arrived at fedex location": TrackingStatus.IN_TRANSIT,
    "at destination sort facility": TrackingStatus.IN_TRANSIT,
    "picked up": TrackingStatus.PRE_TRANSIT,
    "shipment information sent to fedex": TrackingStatus.PRE_TRANSIT,
    "label created": TrackingStatus.PRE_TRANSIT,
    "delivery exception": TrackingStatus.EXCEPTION,
    "clearance delay": TrackingStatus.EXCEPTION,
}

DESCRIPTION_MAPPING: dict[str, TrackingStatus] = {
    "Picked Up": TrackingStatus.PRE_TRANSIT,
    "Shipment information sent to FedEx": TrackingStatus.PRE_TRANSIT,
    "In transit": TrackingStatus.IN_TRANSIT,
    "At local FedEx facility": TrackingStatus.IN_TRANSIT,
    "On FedEx vehicle for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "Out for Delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "Delivered": TrackingStatus.DELIVERED,
    "Delivery exception": TrackingStatus.EXCEPTION,
}


class FedExProvider(CarrierProvider):
    """FedEx tracking provider via web scraping."""

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.FEDEX

    @property
    def name(self) -> str:
        return "FedEx"

    def tracking_url(self, tracking_number: str) -> str:
        return FEDEX_TRACKING_PAGE.format(tracking_number=tracking_number)

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate FedEx tracking number format."""
        tn = tracking_number.strip()
        if re.match(r"^\d{12,15}$", tn):
            return True
        if re.match(r"^(96\d{18,20})$", tn):
            return True
        if re.match(r"^DT\d{12}$", tn, re.IGNORECASE):
            return True
        return False

    async def async_track(
        self, tracking_number: str, browser: Browser
    ) -> TrackingResult:
        """Track a FedEx package by scraping the tracking page."""
        result = TrackingResult(
            carrier=Carrier.FEDEX,
            tracking_number=tracking_number,
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            _api_data: dict | None = None

            async def _on_response(response) -> None:
                nonlocal _api_data
                if _api_data is None and "trackingCal" in response.url:
                    try:
                        _api_data = await response.json()
                    except Exception:
                        pass

            page.on("response", _on_response)

            # Warm-up: visit homepage to establish session/cookies before
            # hitting the tracking page (mitigates Akamai bot detection)
            await page.goto(
                "https://www.fedex.com/en-us/home.html",
                wait_until="domcontentloaded",
                timeout=30000,
            )

            url = self.tracking_url(tracking_number)
            await page.goto(url, wait_until="networkidle", timeout=30000)

            if _api_data is not None:
                # JSON path: API response captured during navigation — skip
                # wait_for_selector entirely to avoid TargetClosedError
                self._parse_tracking_json(_api_data, result)
            else:
                # HTML fallback: wait for DOM element then parse page content
                await page.wait_for_selector(WAIT_SELECTOR, timeout=45000)
                html = await page.content()
                self._parse_tracking_page(html, result)

            result.last_updated = datetime.now()
            return result
        finally:
            await context.close()

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        """Parse the FedEx tracking page HTML."""
        soup = BeautifulSoup(html, "html.parser")

        status_el = soup.select_one(
            ".shipment-status-progress .status__title, "
            ".tracking-result .status-label, "
            ".shipment-status .status-text"
        )
        if status_el:
            raw_status = status_el.get_text(strip=True)
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        eta_el = soup.select_one(
            ".shipment-status-progress .delivery__date, "
            ".tracking-result .delivery-date, "
            ".estimated-delivery .date-value"
        )
        if eta_el:
            eta_text = eta_el.get_text(strip=True)
            result.estimated_delivery = self._parse_date(eta_text)

        event_rows = soup.select(
            ".travel-history .scan-event, "
            ".tracking-result .scan-row, "
            ".shipment-activities .activity-row"
        )
        for row in event_rows:
            event = self._parse_scan_row(row)
            if event:
                result.events.append(event)

    def _parse_tracking_json(self, data: dict, result: TrackingResult) -> None:
        """Parse FedEx internal tracking JSON from the /trackingCal/track API."""
        try:
            pkg = data["TrackPackagesResponse"]["packageList"][0]
        except (KeyError, IndexError):
            return

        key_status = pkg.get("keyStatus", "")
        if key_status:
            result.raw_status = key_status
            result.status = self._map_status(key_status)

        eta_str = pkg.get("displayEstDeliveryDateTime", "")
        if eta_str:
            # Strip time component if present (e.g. "01/15/2025 00:00:00")
            result.estimated_delivery = self._parse_date(eta_str.split(" ")[0])

        for scan in pkg.get("scanEventList", []):
            description = scan.get("eventDescription", "")
            location = scan.get("scanLocation", "")
            date_str = scan.get("date", "")
            time_str = scan.get("time", "")

            timestamp = datetime.now()
            if date_str:
                combined = f"{date_str} {time_str}".strip()
                try:
                    timestamp = datetime.strptime(combined, "%m/%d/%Y %I:%M %p")
                except ValueError:
                    parsed = self._parse_date(date_str)
                    if parsed:
                        timestamp = parsed

            status = self._map_status(description)
            result.events.append(
                TrackingEvent(
                    timestamp=timestamp,
                    location=location,
                    description=description,
                    status=status,
                )
            )

    def _map_status(self, raw_status: str) -> TrackingStatus:
        """Map a raw status string to TrackingStatus."""
        lower = raw_status.lower()
        for key, status in STATUS_MAPPING.items():
            if key in lower:
                return status
        return TrackingStatus.UNKNOWN

    def _parse_date(self, text: str) -> datetime | None:
        """Try to parse a date from FedEx date text."""
        formats = [
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%A, %B %d, %Y",
            "%A %m/%d/%Y",
        ]
        cleaned = re.sub(
            r"(Estimated delivery|Scheduled delivery|by|on)\s*:?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None

    def _parse_scan_row(self, row) -> TrackingEvent | None:
        """Parse a single scan event row from FedEx tracking history."""
        desc_el = row.select_one(
            ".scan-event__description, .scan-description, .activity-description"
        )
        loc_el = row.select_one(
            ".scan-event__location, .scan-location, .activity-location"
        )
        date_el = row.select_one(
            ".scan-event__date, .scan-date, .activity-date"
        )

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
