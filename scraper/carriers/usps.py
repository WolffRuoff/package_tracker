"""USPS carrier provider using web scraping."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus
from ..util import utcnow
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

USPS_TRACKING_PAGE = (
    "https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
)

# USPS serves multiple page layouts (varies by IP/geo/AB-test):
#   v1 — legacy widget: ``.track-statusbar`` / ``.current-tracking-status-wrapper``
#   v2 — progress-bar page: ``.tracking-progress-bar-status-container``
# Across the v1->v2 redesign the *wrapper* classes changed but the *leaf* classes
# (.tb-step / .tb-status / .expected_delivery) did not, so we wait on the leaves
# (plus the known wrappers) — this survives future wrapper renames.
WAIT_SELECTOR = (
    ".tb-step, .tb-status, .expected_delivery, "
    ".track-statusbar, .tracking-progress-bar-status-container"
)

STATUS_MAPPING: dict[str, TrackingStatus] = {
    "delivered": TrackingStatus.DELIVERED,
    "out for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "in transit": TrackingStatus.IN_TRANSIT,
    "moving through network": TrackingStatus.IN_TRANSIT,
    "on the way": TrackingStatus.IN_TRANSIT,
    "arrived": TrackingStatus.IN_TRANSIT,
    "departed": TrackingStatus.IN_TRANSIT,
    "preparing for delivery": TrackingStatus.IN_TRANSIT,
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

        url = self.tracking_url(tracking_number)
        html = await self._get_page_content(browser, url, WAIT_SELECTOR)
        self._parse_tracking_page(html, result)
        result.last_updated = utcnow()
        return result

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        """Parse the USPS tracking page HTML (handles both page layouts)."""
        soup = BeautifulSoup(html, "html.parser")

        self._parse_status(soup, result)

        eta_snip = soup.select_one(".expected_delivery .eta_snip")
        if eta_snip:
            for hint in eta_snip.select(".hint"):
                hint.decompose()
            eta_text = eta_snip.get_text(" ", strip=True)
            result.estimated_delivery = self._parse_date(eta_text)

        # Event rows are ".tb-step" in every known layout. Match them directly
        # rather than scoping to a wrapper container (the wrappers are what
        # change between versions); dedup in case a page repeats a step.
        history_rows = soup.select(".tb-step")
        seen: set[tuple[str, str, str]] = set()
        for row in history_rows:
            event = self._parse_event_row(row)
            if not event:
                continue
            key = (event.description, event.location, str(event.timestamp))
            if key in seen:
                continue
            seen.add(key)
            result.events.append(event)

    def _parse_status(self, soup, result: TrackingResult) -> None:
        """Populate result.status / raw_status from whichever layout is present.

        Primary signal is the human-readable status text carried by the stable
        leaf classes (``.tb-status`` / ``.tb-status-detail``), which survived the
        v1->v2 rename. The v2 container's ``<state>-status`` modifier class is
        only a fallback for status text we don't recognise.
        """
        banner = (
            # v1: explicit status banner.
            soup.select_one(".current-tracking-status-wrapper .tb-status")
            # v2: the current step's short status, then its detail.
            or soup.select_one(".tb-step.current-step .tb-status")
            or soup.select_one(".tb-step.current-step .tb-status-detail")
        )
        if banner:
            raw_status = banner.get_text(strip=True)
            result.raw_status = raw_status
            result.status = self._map_status(raw_status)

        # Fallback: derive status from the container modifier class (e.g.
        # "in-transit-status") when the text didn't classify.
        if result.status == TrackingStatus.UNKNOWN:
            container = soup.select_one(".tracking-progress-bar-status-container")
            if container:
                for cls in container.get("class", []):
                    if cls.endswith("-status"):
                        mapped = self._map_status(
                            cls[: -len("-status")].replace("-", " ")
                        )
                        if mapped != TrackingStatus.UNKNOWN:
                            result.status = mapped
                            break

    def _map_status(self, raw_status: str) -> TrackingStatus:
        """Map a raw status string to TrackingStatus."""
        lower = raw_status.lower()
        for key, status in STATUS_MAPPING.items():
            if key in lower:
                return status
        return TrackingStatus.UNKNOWN

    def _parse_date(self, text: str) -> datetime | None:
        """Try to parse a date from text like 'January 15, 2025' or 'Friday, March 7'."""
        # Word boundaries keep "on" from matching inside e.g. "Monday".
        cleaned = re.sub(
            r"\b(Expected Delivery\s*(?:by)?|by|on)\b\s*:?\s*", "", text
        ).strip()
        cleaned = re.sub(
            r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*",
            "",
            cleaned,
        ).strip()
        # New USPS event dates carry a clock time, e.g. "July 8, 2026 9:49 AM".
        cleaned = re.sub(
            r"\s+\d{1,2}:\d{2}\s*(?:[AaPp][Mm])?$", "", cleaned
        ).strip()

        for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue

        for fmt in ("%B %d", "%b %d"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                return parsed.replace(year=utcnow().year)
            except ValueError:
                continue

        return None

    def _parse_event_row(self, row) -> TrackingEvent | None:
        """Parse a single tracking event row from the history."""
        # Prefer the detailed description; the short ".tb-status" (e.g. "On the
        # Way") is only a fallback. A plain comma selector would return whichever
        # comes first in the DOM, which is the short one on the new layout.
        desc_el = row.select_one(".tb-status-detail") or row.select_one(".tb-status")
        date_el = row.select_one(".tb-date, .tb-date-time")
        loc_el = row.select_one(".tb-location")

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
