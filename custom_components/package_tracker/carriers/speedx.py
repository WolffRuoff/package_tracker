"""SpeedX carrier provider — validation and URL only."""

from __future__ import annotations

import re

from ..const import Carrier
from .base import CarrierProvider

SPEEDX_TRACKING_PAGE = "https://tracking.speedx.io/{tracking_number}"


class SpeedXProvider(CarrierProvider):
    """SpeedX tracking provider (validation + URL)."""

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
