"""SpeedX carrier provider using web scraping."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus
from ..util import utcnow
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

SPEEDX_TRACKING_PAGE = "https://tracking.speedx.io/{tracking_number}"
WAIT_SELECTOR = "img[alt='warehouse']"


class SpeedXProvider(CarrierProvider):
    """SpeedX tracking provider via web scraping."""

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.SPEEDX

    @property
    def name(self) -> str:
        return "SpeedX"

    def tracking_url(self, tracking_number: str) -> str:
        return SPEEDX_TRACKING_PAGE.format(tracking_number=tracking_number.upper())

    def validate_tracking_number(self, tracking_number: str) -> bool:
        tn = tracking_number.strip().upper()
        return bool(re.match(r"^SPX[A-Z]{2,5}\d{8,15}$", tn))

    async def async_track(self, tracking_number: str, browser: Browser) -> TrackingResult:
        """Track a SpeedX package by scraping the tracking page."""
        result = TrackingResult(carrier=Carrier.SPEEDX, tracking_number=tracking_number)
        url = self.tracking_url(tracking_number)
        html = await self._get_page_content(browser, url, WAIT_SELECTOR)
        self._parse_tracking_page(html, result)
        result.last_updated = utcnow()
        return result

    def _parse_tracking_page(self, html: str, result: TrackingResult) -> None:
        soup = BeautifulSoup(html, "html.parser")
        events_data = self._extract_events_json(soup)
        if not events_data:
            return

        first = events_data[0]
        category = first.get("category", "")
        event_desc = first.get("eventDescription", "")
        result.raw_status = event_desc
        result.status = self._map_status(category, event_desc)

        edd_text = self._extract_edd(soup)
        if edd_text:
            result.estimated_delivery = self._parse_delivery_date(edd_text)

        for ev in events_data:
            event = self._parse_event(ev)
            if event:
                result.events.append(event)

    def _extract_events_json(self, soup) -> list | None:
        """Find and decode events array from Next.js RSC script tags."""
        for script in soup.find_all("script"):
            text = script.get_text()
            if 'trackingNumber' not in text or 'events' not in text:
                continue
            try:
                unescaped = text.replace('\\"', '"').replace('\\\\', '\\')
                idx = unescaped.find('"events":')
                if idx < 0:
                    continue
                bracket_idx = unescaped.index('[', idx)
                decoder = json.JSONDecoder()
                events, _ = decoder.raw_decode(unescaped, bracket_idx)
                return events
            except (ValueError, json.JSONDecodeError):
                continue
        return None

    def _extract_edd(self, soup) -> str | None:
        """Extract edd field from Next.js RSC script tags."""
        for script in soup.find_all("script"):
            text = script.get_text()
            if 'edd' not in text:
                continue
            unescaped = text.replace('\\"', '"')
            match = re.search(r'"edd":"([^"]+)"', unescaped)
            if match:
                return match.group(1)
        return None

    def _map_status(self, category: str, event_description: str) -> TrackingStatus:
        if category == "LAST_MILE_DELIVERED":
            return TrackingStatus.DELIVERED
        if category == "LAST_MILE_ENROUTE":
            if "out for delivery" in event_description.lower():
                return TrackingStatus.OUT_FOR_DELIVERY
            return TrackingStatus.IN_TRANSIT
        if category == "PICKUP":
            return TrackingStatus.PRE_TRANSIT
        return TrackingStatus.UNKNOWN

    def _parse_delivery_date(self, edd_text: str) -> datetime | None:
        cleaned = re.sub(r'^(Delivered|Estimated Delivery Date):\s*', '', edd_text).strip()
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None

    def _parse_event(self, ev: dict) -> TrackingEvent | None:
        try:
            ts = datetime.fromisoformat(ev["localTs"])
        except (KeyError, ValueError):
            ts = utcnow()
        description = ev.get("description", ev.get("eventDescription", ""))
        location = ev.get("location", "")
        category = ev.get("category", "")
        event_desc = ev.get("eventDescription", "")
        status = self._map_status(category, event_desc)
        return TrackingEvent(
            timestamp=ts,
            location=location,
            description=description,
            status=status,
        )
