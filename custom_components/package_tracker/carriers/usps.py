"""USPS carrier provider — validation and URL only."""

from __future__ import annotations

import re

from ..const import Carrier
from .base import CarrierProvider

USPS_TRACKING_PAGE = (
    "https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
)


class USPSProvider(CarrierProvider):
    """USPS tracking provider (validation + URL)."""

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
