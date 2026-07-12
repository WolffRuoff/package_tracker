"""UPS carrier provider using web scraping."""

from __future__ import annotations

import asyncio
import logging
import re

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from ..const import Carrier
from ..util import utcnow
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

UPS_TRACKING_PAGE = (
    "https://www.ups.com/track?tracknum={tracking_number}"
    "&requester=ST/trackdetails"
)

# DOM fallback only (see _parse_tracking_json) — status label and error banner ids.
WAIT_SELECTOR = "#stApp_nameKey, #stApp_error_tittle2"


class UPSProvider(CarrierProvider):
    """UPS tracking provider via web scraping."""

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.UPS

    @property
    def name(self) -> str:
        return "UPS"

    def tracking_url(self, tracking_number: str) -> str:
        return UPS_TRACKING_PAGE.format(tracking_number=tracking_number)

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate UPS tracking number format (1Z + 16 alphanumeric chars)."""
        tn = tracking_number.strip().upper()
        return bool(re.match(r"^1Z[A-Z0-9]{16}$", tn))

    async def async_track(
        self, tracking_number: str, browser: Browser
    ) -> TrackingResult:
        """Track a UPS package by intercepting the tracking page's Track/GetStatus API call."""
        result = TrackingResult(
            carrier=Carrier.UPS,
            tracking_number=tracking_number,
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            _api_data: dict | None = None
            _api_event = asyncio.Event()

            async def _on_response(response) -> None:
                nonlocal _api_data
                if _api_data is None and "Track/GetStatus" in response.url:
                    try:
                        _api_data = await response.json()
                        _api_event.set()
                    except Exception as exc:
                        _LOGGER.warning(
                            "UPS: failed to parse GetStatus response for %s: %s",
                            tracking_number,
                            exc,
                        )

            page.on("response", _on_response)

            url = self.tracking_url(tracking_number)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if not _api_event.is_set():
                try:
                    await asyncio.wait_for(_api_event.wait(), timeout=45.0)
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "UPS: GetStatus response not captured for %s", tracking_number
                    )

            if _api_data is not None:
                self._parse_tracking_json(_api_data, result)
            else:
                await page.wait_for_selector(WAIT_SELECTOR, timeout=45000)
                html = await page.content()
                self._parse_tracking_page(html, result)

            result.last_updated = utcnow()
            return result
        finally:
            await context.close()

    def _parse_tracking_json(self, data: dict, result: TrackingResult) -> None:
        """Parse UPS tracking JSON from the Track/GetStatus API."""
        try:
            pkg = data["trackDetails"][0]
        except (KeyError, IndexError, TypeError):
            return

        if pkg.get("errorCode"):
            return

        raw_status = pkg.get("packageStatus") or ""
        if raw_status:
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        for activity in pkg.get("shipmentProgressActivities") or []:
            description = (activity.get("activityScan") or "").strip()
            timestamp = self._parse_ups_datetime(
                activity.get("date", ""), activity.get("time", "")
            )
            result.events.append(
                TrackingEvent(
                    timestamp=timestamp or utcnow(),
                    location=activity.get("location", ""),
                    description=description,
                    status=self._map_status(description),
                )
            )

        # Activities are newest-first, so events[0] is the current status's date/time.
        if result.events:
            result.estimated_delivery = result.events[0].timestamp

    def _parse_ups_datetime(self, date_str: str, time_str: str):
        """Parse UPS's 'MM/DD/YYYY' + 'H:MM A.M./P.M.' fields into a datetime."""
        combined = f"{date_str} {time_str}".replace("A.M.", "AM").replace("P.M.", "PM").strip()
        return self._parse_date(combined)

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        """Parse the UPS tracking page HTML (fallback; the DOM has no shipment history)."""
        soup = BeautifulSoup(html, "html.parser")

        status_el = soup.select_one("#stApp_nameKey")
        if status_el:
            raw_status = status_el.get_text(strip=True)
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        month_el = soup.select_one("#st_App_PkgStsMonthNum")
        time_el = soup.select_one("#st_App_PkgStsTime")
        if month_el and time_el:
            result.estimated_delivery = self._parse_ups_datetime(
                month_el.get_text(strip=True), time_el.get_text(strip=True)
            )
