"""FedEx carrier provider — validation and URL only."""

from __future__ import annotations

import re

from ..const import Carrier
from .base import CarrierProvider

FEDEX_TRACKING_PAGE = "https://www.fedex.com/fedextrack/?trknbr={tracking_number}"


class FedExProvider(CarrierProvider):
    """FedEx tracking provider (validation + URL)."""

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
