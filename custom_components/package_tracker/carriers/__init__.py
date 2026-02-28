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


def get_provider(carrier: Carrier, **kwargs: str) -> CarrierProvider:
    """Create a carrier provider instance with the given credentials."""
    provider_cls = CARRIER_PROVIDERS[carrier]

    if carrier == Carrier.USPS:
        return provider_cls(api_key=kwargs["api_key"])
    if carrier == Carrier.UPS:
        return provider_cls(
            client_id=kwargs["client_id"],
            client_secret=kwargs["client_secret"],
        )
    if carrier == Carrier.FEDEX:
        return provider_cls(
            api_key=kwargs["api_key"],
            secret_key=kwargs["secret_key"],
        )

    raise ValueError(f"Unknown carrier: {carrier}")


def detect_carrier(tracking_number: str) -> Carrier | None:
    """Detect the carrier from a tracking number format.

    Returns the first matching carrier or None.
    """
    for carrier, provider_cls in CARRIER_PROVIDERS.items():
        # Create a temporary instance just for validation
        # Use dummy credentials since we only need validate_tracking_number
        try:
            if carrier == Carrier.USPS:
                provider = provider_cls(api_key="")
            elif carrier == Carrier.UPS:
                provider = provider_cls(client_id="", client_secret="")
            elif carrier == Carrier.FEDEX:
                provider = provider_cls(api_key="", secret_key="")
            else:
                continue

            if provider.validate_tracking_number(tracking_number):
                return carrier
        except Exception:  # noqa: BLE001
            continue

    return None
