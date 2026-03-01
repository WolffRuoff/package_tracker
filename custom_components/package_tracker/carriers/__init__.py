"""Carrier provider registry and factory."""

from __future__ import annotations

from ..const import Carrier
from .base import CarrierProvider
from .fedex import FedExProvider
from .ups import UPSProvider
from .usps import USPSProvider

CARRIER_PROVIDERS: dict[Carrier, type[CarrierProvider]] = {
    Carrier.USPS: USPSProvider,
    Carrier.UPS: UPSProvider,
    Carrier.FEDEX: FedExProvider,
}


def get_provider(carrier: Carrier) -> CarrierProvider:
    """Create a carrier provider instance."""
    provider_cls = CARRIER_PROVIDERS.get(carrier)
    if provider_cls is None:
        raise ValueError(f"Unknown carrier: {carrier}")
    return provider_cls()


def detect_carrier(tracking_number: str) -> Carrier | None:
    """Detect the carrier from a tracking number format.

    Returns the first matching carrier or None.
    """
    for carrier, provider_cls in CARRIER_PROVIDERS.items():
        try:
            provider = provider_cls()
            if provider.validate_tracking_number(tracking_number):
                return carrier
        except Exception:  # noqa: BLE001
            continue

    return None
