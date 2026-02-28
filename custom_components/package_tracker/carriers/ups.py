"""UPS carrier provider using Tracking API v1."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import aiohttp

from ..const import Carrier, TrackingStatus
from .base import CarrierProvider, TrackingEvent, TrackingResult

_LOGGER = logging.getLogger(__name__)

UPS_TOKEN_URL = "https://onlinetools.ups.com/security/v1/oauth/token"
UPS_TRACKING_URL = "https://onlinetools.ups.com/api/track/v1/details/{tracking_number}"

# UPS status type codes
STATUS_MAPPING: dict[str, TrackingStatus] = {
    "M": TrackingStatus.PRE_TRANSIT,  # Manifest/Billing info received
    "P": TrackingStatus.PRE_TRANSIT,  # Pickup
    "I": TrackingStatus.IN_TRANSIT,   # In Transit
    "O": TrackingStatus.OUT_FOR_DELIVERY,
    "D": TrackingStatus.DELIVERED,
    "X": TrackingStatus.EXCEPTION,
    "RS": TrackingStatus.EXCEPTION,   # Returned to shipper
    "MV": TrackingStatus.IN_TRANSIT,  # Moved
    "NA": TrackingStatus.UNKNOWN,
}


class UPSProvider(CarrierProvider):
    """UPS tracking provider."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        """Initialize with UPS OAuth credentials."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    @property
    def carrier_id(self) -> Carrier:
        return Carrier.UPS

    @property
    def name(self) -> str:
        return "UPS"

    @property
    def requires_api_key(self) -> bool:
        return True

    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Validate UPS tracking number format (1Z + 16 alphanumeric chars)."""
        tn = tracking_number.strip().upper()
        return bool(re.match(r"^1Z[A-Z0-9]{16}$", tn))

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
                UPS_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=aiohttp.BasicAuth(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        self._access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        from datetime import timedelta

        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)

    async def async_track(self, tracking_number: str) -> TrackingResult:
        """Track a UPS package."""
        result = TrackingResult(
            carrier=Carrier.UPS,
            tracking_number=tracking_number,
        )

        try:
            await self._ensure_token()

            url = UPS_TRACKING_URL.format(tracking_number=tracking_number)
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "transId": f"pt-{tracking_number}",
                "transactionSrc": "package_tracker",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            shipment = (
                data.get("trackResponse", {})
                .get("shipment", [{}])[0]
            )
            package = shipment.get("package", [{}])[0]

            # Current status
            current = package.get("currentStatus", {})
            status_code = current.get("type", "NA")
            result.raw_status = current.get("description", "")
            result.status = STATUS_MAPPING.get(status_code, TrackingStatus.UNKNOWN)

            # Estimated delivery
            delivery_date = package.get("deliveryDate", [{}])
            if delivery_date:
                date_str = delivery_date[0].get("date", "")
                if date_str:
                    try:
                        result.estimated_delivery = datetime.strptime(
                            date_str, "%Y%m%d"
                        )
                    except ValueError:
                        pass

            # Activity/events
            for activity in package.get("activity", []):
                event = self._parse_activity(activity)
                if event:
                    result.events.append(event)

            result.last_updated = datetime.now()

        except Exception:
            _LOGGER.exception("Error tracking UPS package %s", tracking_number)

        return result

    def _parse_activity(self, activity: dict) -> TrackingEvent | None:
        """Parse an activity entry into a TrackingEvent."""
        status_obj = activity.get("status", {})
        status_code = status_obj.get("type", "NA")
        description = status_obj.get("description", "")

        location_obj = activity.get("location", {}).get("address", {})
        location_parts = [
            location_obj.get("city", ""),
            location_obj.get("stateProvince", ""),
            location_obj.get("countryCode", ""),
        ]
        location = ", ".join(p for p in location_parts if p)

        date_str = activity.get("date", "")
        time_str = activity.get("time", "")
        timestamp = datetime.now()
        if date_str:
            try:
                dt_str = f"{date_str} {time_str}" if time_str else date_str
                fmt = "%Y%m%d %H%M%S" if time_str else "%Y%m%d"
                timestamp = datetime.strptime(dt_str, fmt)
            except ValueError:
                pass

        return TrackingEvent(
            timestamp=timestamp,
            location=location,
            description=description,
            status=STATUS_MAPPING.get(status_code, TrackingStatus.UNKNOWN),
        )
