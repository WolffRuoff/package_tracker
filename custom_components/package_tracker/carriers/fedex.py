"""FedEx carrier provider using Track API."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import aiohttp

from ..const import Carrier, TrackingStatus
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

FEDEX_TOKEN_URL = "https://apis.fedex.com/oauth/token"
FEDEX_TRACK_URL = "https://apis.fedex.com/track/v1/trackingnumbers"

STATUS_MAPPING: dict[str, TrackingStatus] = {
    "PU": TrackingStatus.PRE_TRANSIT,
    "OC": TrackingStatus.PRE_TRANSIT,
    "IT": TrackingStatus.IN_TRANSIT,
    "IX": TrackingStatus.IN_TRANSIT,
    "AR": TrackingStatus.IN_TRANSIT,
    "DP": TrackingStatus.IN_TRANSIT,
    "OD": TrackingStatus.OUT_FOR_DELIVERY,
    "DL": TrackingStatus.DELIVERED,
    "DE": TrackingStatus.EXCEPTION,
    "CA": TrackingStatus.EXCEPTION,
    "SE": TrackingStatus.EXCEPTION,
    "CD": TrackingStatus.EXCEPTION,
}

# Higher-level status descriptions from FedEx
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
    """FedEx tracking provider."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        """Initialize with FedEx API credentials."""
        self._api_key = api_key
        self._secret_key = secret_key
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.FEDEX

    @property
    def name(self) -> str:
        return "FedEx"

    @property
    def requires_api_key(self) -> bool:
        return True

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate FedEx tracking number format."""
        tn = tracking_number.strip()
        # 12-15 digit numeric (Express/Ground)
        if re.match(r"^\d{12,15}$", tn):
            return True
        # 20-22 digit numeric (SmartPost/96 prefix)
        if re.match(r"^(96\d{18,20})$", tn):
            return True
        # Door tag numbers (DT prefix)
        if re.match(r"^DT\d{12}$", tn, re.IGNORECASE):
            return True
        return False

    async def _ensure_token(self) -> None:
        """Obtain or refresh the OAuth access token."""
        if (
            self._access_token
            and self._token_expires
            and datetime.now() < self._token_expires
        ):
            return

        async with aiohttp.ClientSession() as session:
            async with session.post(
                FEDEX_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._api_key,
                    "client_secret": self._secret_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        self._access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        from datetime import timedelta

        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)

    async def async_track(self, tracking_number: str) -> TrackingResult:
        """Track a FedEx package."""
        result = TrackingResult(
            carrier=Carrier.FEDEX,
            tracking_number=tracking_number,
        )

        try:
            await self._ensure_token()

            payload = {
                "trackingInfo": [
                    {
                        "trackingNumberInfo": {
                            "trackingNumber": tracking_number,
                        }
                    }
                ],
                "includeDetailedScans": True,
            }

            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    FEDEX_TRACK_URL, json=payload, headers=headers
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            results = (
                data.get("output", {})
                .get("completeTrackResults", [{}])[0]
                .get("trackResults", [{}])[0]
            )

            # Check for errors
            error = results.get("error")
            if error:
                _LOGGER.warning(
                    "FedEx tracking error: %s", error.get("message", "Unknown")
                )
                result.raw_status = error.get("message", "Error")
                return result

            # Latest status
            latest = results.get("latestStatusDetail", {})
            scan_code = latest.get("code", "")
            description = latest.get("description", "")
            result.raw_status = description

            # Try scan code first, then description
            result.status = STATUS_MAPPING.get(
                scan_code,
                DESCRIPTION_MAPPING.get(description, TrackingStatus.UNKNOWN),
            )

            # Estimated delivery
            delivery_dates = results.get("estimatedDeliveryTimeWindow", {})
            delivery_window = delivery_dates.get("window", {})
            ends = delivery_window.get("ends")
            if ends:
                try:
                    result.estimated_delivery = datetime.fromisoformat(
                        ends.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # Scan events
            for scan in results.get("scanEvents", []):
                event = self._parse_scan(scan)
                if event:
                    result.events.append(event)

            result.last_updated = datetime.now()

        except Exception:
            _LOGGER.exception("Error tracking FedEx package %s", tracking_number)

        return result

    def _parse_scan(self, scan: dict) -> TrackingEvent | None:
        """Parse a scan event into a TrackingEvent."""
        description = scan.get("eventDescription", "")
        scan_code = scan.get("derivedStatusCode", scan.get("eventType", ""))

        location_obj = scan.get("scanLocation", {})
        location_parts = [
            location_obj.get("city", ""),
            location_obj.get("stateOrProvinceCode", ""),
            location_obj.get("countryCode", ""),
        ]
        location = ", ".join(p for p in location_parts if p)

        timestamp = datetime.now()
        date_str = scan.get("date")
        if date_str:
            try:
                timestamp = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        status = STATUS_MAPPING.get(
            scan_code,
            DESCRIPTION_MAPPING.get(description, TrackingStatus.UNKNOWN),
        )

        return TrackingEvent(
            timestamp=timestamp,
            location=location,
            description=description,
            status=status,
        )
