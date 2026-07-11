"""UPS carrier provider using web scraping."""

from __future__ import annotations

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

WAIT_SELECTOR = "#stApp .ups-track_details, #stApp .ups-alert, #stApp .track-no-info-content"


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
        """Track a UPS package by scraping the tracking page."""
        result = TrackingResult(
            carrier=Carrier.UPS,
            tracking_number=tracking_number,
        )

        url = self.tracking_url(tracking_number)
        html = await self._get_page_content(browser, url, WAIT_SELECTOR)
        self._parse_tracking_page(html, result)
        result.last_updated = utcnow()
        return result

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        """Parse the UPS tracking page HTML."""
        soup = BeautifulSoup(html, "html.parser")

        status_el = soup.select_one(
            ".ups-track_details .ups-txt_status, "
            ".st_App-head .ups-txt_status, "
            ".track-status-header"
        )
        if status_el:
            raw_status = status_el.get_text(strip=True)
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        eta_el = soup.select_one(
            ".ups-est_delivery .ups-txt_date, "
            ".est-delivery .delivery-date, "
            ".ups-track_details .ups-txt_eta"
        )
        if eta_el:
            eta_text = eta_el.get_text(strip=True)
            result.estimated_delivery = self._parse_date(eta_text)

        activity_rows = soup.select(
            ".ups-shipment_progress .ups-progress_row, "
            "#stApp .activity-row, "
            ".ups-activity_table tbody tr"
        )
        for row in activity_rows:
            event = self._parse_activity_row(row)
            if event:
                result.events.append(event)

    def _parse_activity_row(self, row) -> TrackingEvent | None:
        """Parse a single activity row from UPS tracking history."""
        desc_el = row.select_one(
            ".ups-txt_activity, .activity-description, td:nth-child(1)"
        )
        loc_el = row.select_one(
            ".ups-txt_location, .activity-location, td:nth-child(2)"
        )
        date_el = row.select_one(
            ".ups-txt_date, .activity-date, td:nth-child(3)"
        )

        description = desc_el.get_text(strip=True) if desc_el else ""
        location = loc_el.get_text(strip=True) if loc_el else ""

        timestamp = utcnow()
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
