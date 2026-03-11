"""FedEx carrier provider using web scraping."""

from __future__ import annotations

import asyncio
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
            _api_event = asyncio.Event()

            async def _on_response(response) -> None:
                nonlocal _api_data
                url = response.url
                if _api_data is None and (
                    "trackingCal" in url
                    or "api.fedex.com/track/" in url
                ):
                    try:
                        _api_data = await response.json()
                        _LOGGER.info("FedEx: captured API response from %s", url)
                        _api_event.set()
                    except Exception as exc:
                        _LOGGER.warning("FedEx: failed to parse %s: %s", url, exc)

            page.on("response", _on_response)

            # Warm-up: visit homepage to establish session/cookies before
            # hitting the tracking page (mitigates bot detection)
            await page.goto(
                "https://www.fedex.com/en-us/home.html",
                wait_until="domcontentloaded",
                timeout=30000,
            )

            tracking_url = self.tracking_url(tracking_number)
            # domcontentloaded so we don't block on networkidle before the
            # tracking API fires; the asyncio.Event below handles the wait
            await page.goto(tracking_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for the tracking API response — may fire during or after goto
            if not _api_event.is_set():
                try:
                    await asyncio.wait_for(_api_event.wait(), timeout=45.0)
                except asyncio.TimeoutError:
                    _LOGGER.warning("FedEx: API response not captured for %s", tracking_number)

            if _api_data is not None:
                # JSON path: skip wait_for_selector entirely
                self._parse_tracking_json(_api_data, result)
            else:
                # HTML fallback
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
        """Parse FedEx tracking JSON from the api.fedex.com/track/v2/shipments API."""
        try:
            pkg = data["output"]["packages"][0]
        except (KeyError, IndexError):
            return

        # mainStatus is the human-readable status ("Picked up", "Delivered", etc.)
        main_status = pkg.get("mainStatus", "")
        if main_status:
            result.raw_status = main_status
            result.status = self._map_status(main_status)

        # estDeliveryDt is ISO-8601 — reliable for parsing; strip timezone for naive datetime
        est_dt = pkg.get("estDeliveryDt", "")
        if est_dt:
            try:
                result.estimated_delivery = datetime.fromisoformat(est_dt).replace(tzinfo=None)
            except ValueError:
                pass

        for scan in pkg.get("scanEventList", []):
            description = scan.get("status", "")
            location = scan.get("scanLocation", "")
            date_str = scan.get("date", "")  # "YYYY-MM-DD"
            time_str = scan.get("time", "")  # "HH:MM:SS"

            timestamp = datetime.now()
            if date_str:
                combined = f"{date_str}T{time_str}" if time_str else date_str
                try:
                    timestamp = datetime.fromisoformat(combined)
                except ValueError:
                    try:
                        timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        pass

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
