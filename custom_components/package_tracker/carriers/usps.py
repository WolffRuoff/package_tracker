"""USPS carrier provider using Web Tools Tracking API."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from xml.etree import ElementTree

import aiohttp

from ..const import Carrier, TrackingStatus
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

USPS_TRACKING_URL = "https://secure.shippingapis.com/ShippingAPI.dll"

STATUS_MAPPING: dict[str, TrackingStatus] = {
    "Delivered": TrackingStatus.DELIVERED,
    "Out for Delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "In Transit": TrackingStatus.IN_TRANSIT,
    "In Transit to Next Facility": TrackingStatus.IN_TRANSIT,
    "Arrived at Post Office": TrackingStatus.IN_TRANSIT,
    "Arrived at USPS Facility": TrackingStatus.IN_TRANSIT,
    "Departed Post Office": TrackingStatus.IN_TRANSIT,
    "Departed USPS Facility": TrackingStatus.IN_TRANSIT,
    "Acceptance": TrackingStatus.PRE_TRANSIT,
    "Accepted at USPS Origin Facility": TrackingStatus.PRE_TRANSIT,
    "Pre-Shipment Info Sent to USPS": TrackingStatus.PRE_TRANSIT,
    "Shipping Label Created": TrackingStatus.PRE_TRANSIT,
    "USPS in possession of item": TrackingStatus.IN_TRANSIT,
    "Alert": TrackingStatus.EXCEPTION,
    "Notice Left": TrackingStatus.EXCEPTION,
    "Delivery Attempt": TrackingStatus.EXCEPTION,
}


class USPSProvider(CarrierProvider):
    """USPS tracking provider."""

    def __init__(self, api_key: str) -> None:
        """Initialize with USPS Web Tools user ID."""
        self._api_key = api_key

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.USPS

    @property
    def name(self) -> str:
        return "USPS"

    @property
    def requires_api_key(self) -> bool:
        return True

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate USPS tracking number format."""
        tn = tracking_number.strip().upper()
        # 20-22 digit numeric
        if re.match(r"^\d{20,22}$", tn):
            return True
        # Service prefix formats (e.g., EA, EC, CP, etc. followed by 9 digits + US)
        if re.match(r"^[A-Z]{2}\d{9}US$", tn):
            return True
        return False

    async def async_track(self, tracking_number: str) -> TrackingResult:
        """Track a USPS package."""
        result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number=tracking_number,
        )

        xml_request = (
            f'<TrackFieldRequest USERID="{self._api_key}">'
            f"<TrackID ID=\"{tracking_number}\"></TrackID>"
            f"</TrackFieldRequest>"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    USPS_TRACKING_URL,
                    params={"API": "TrackV2", "XML": xml_request},
                ) as resp:
                    resp.raise_for_status()
                    text = await resp.text()

            root = ElementTree.fromstring(text)

            error = root.find(".//Error/Description")
            if error is not None:
                _LOGGER.warning("USPS tracking error: %s", error.text)
                result.raw_status = error.text or "Error"
                result.status = TrackingStatus.UNKNOWN
                return result

            track_info = root.find(".//TrackInfo")
            if track_info is None:
                return result

            # Parse summary (most recent status)
            summary = track_info.find("TrackSummary")
            if summary is not None:
                event_text = summary.findtext("Event", "")
                result.raw_status = event_text
                result.status = STATUS_MAPPING.get(event_text, TrackingStatus.UNKNOWN)

                event = self._parse_event(summary)
                if event:
                    result.events.append(event)

            # Parse detail events
            for detail in track_info.findall("TrackDetail"):
                event = self._parse_event(detail)
                if event:
                    result.events.append(event)

            # Parse expected delivery
            expected = track_info.findtext("ExpectedDeliveryDate")
            if expected:
                try:
                    result.estimated_delivery = datetime.strptime(
                        expected, "%B %d, %Y"
                    )
                except ValueError:
                    pass

            result.last_updated = datetime.now()

        except Exception:
            _LOGGER.exception("Error tracking USPS package %s", tracking_number)

        return result

    def _parse_event(self, element: ElementTree.Element) -> TrackingEvent | None:
        """Parse a tracking event from an XML element."""
        event_text = element.findtext("Event", "")
        date_str = element.findtext("EventDate", "")
        time_str = element.findtext("EventTime", "")
        city = element.findtext("EventCity", "")
        state = element.findtext("EventState", "")

        location_parts = [p for p in [city, state] if p]
        location = ", ".join(location_parts)

        timestamp = datetime.now()
        if date_str:
            try:
                dt_str = f"{date_str} {time_str}" if time_str else date_str
                fmt = "%B %d, %Y %I:%M %p" if time_str else "%B %d, %Y"
                timestamp = datetime.strptime(dt_str, fmt)
            except ValueError:
                pass

        status = STATUS_MAPPING.get(event_text, TrackingStatus.UNKNOWN)

        return TrackingEvent(
            timestamp=timestamp,
            location=location,
            description=event_text,
            status=status,
        )
