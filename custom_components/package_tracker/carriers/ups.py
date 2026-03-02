"""UPS carrier provider — validation and URL only."""

from __future__ import annotations

import re

from ..const import Carrier
from .base import CarrierProvider

UPS_TRACKING_PAGE = (
    "https://www.ups.com/track?tracknum={tracking_number}"
    "&requester=ST/trackdetails"
)


class UPSProvider(CarrierProvider):
    """UPS tracking provider (validation + URL)."""

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
