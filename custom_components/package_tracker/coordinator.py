"""DataUpdateCoordinator for Package Tracker."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .carriers import get_provider
from .carriers.base import CarrierProvider, TrackingResult
from .const import (
    CONF_FEDEX_API_KEY,
    CONF_FEDEX_SECRET_KEY,
    CONF_PACKAGES,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_API_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    Carrier,
)

_LOGGER = logging.getLogger(__name__)


class PackageTrackerCoordinator(DataUpdateCoordinator[dict[str, TrackingResult]]):
    """Coordinator that polls all carrier APIs for package updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self._providers: dict[Carrier, CarrierProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize carrier providers from config entry data."""
        data = self.entry.data

        if data.get(CONF_USPS_API_KEY):
            self._providers[Carrier.USPS] = get_provider(
                Carrier.USPS, api_key=data[CONF_USPS_API_KEY]
            )

        if data.get(CONF_UPS_CLIENT_ID) and data.get(CONF_UPS_CLIENT_SECRET):
            self._providers[Carrier.UPS] = get_provider(
                Carrier.UPS,
                client_id=data[CONF_UPS_CLIENT_ID],
                client_secret=data[CONF_UPS_CLIENT_SECRET],
            )

        if data.get(CONF_FEDEX_API_KEY) and data.get(CONF_FEDEX_SECRET_KEY):
            self._providers[Carrier.FEDEX] = get_provider(
                Carrier.FEDEX,
                api_key=data[CONF_FEDEX_API_KEY],
                secret_key=data[CONF_FEDEX_SECRET_KEY],
            )

    def get_packages(self) -> list[dict[str, Any]]:
        """Return the list of tracked packages from options."""
        return list(self.entry.options.get(CONF_PACKAGES, []))

    async def _async_update_data(self) -> dict[str, TrackingResult]:
        """Fetch tracking data for all packages."""
        packages = self.get_packages()
        results: dict[str, TrackingResult] = {}

        # Preserve previous data as fallback
        previous = self.data or {}

        for pkg in packages:
            tracking_number = pkg["tracking_number"]
            carrier = Carrier(pkg["carrier"])

            provider = self._providers.get(carrier)
            if not provider:
                _LOGGER.warning(
                    "No provider configured for carrier %s (package %s)",
                    carrier,
                    tracking_number,
                )
                # Keep previous data if available
                if tracking_number in previous:
                    results[tracking_number] = previous[tracking_number]
                continue

            try:
                result = await provider.async_track(tracking_number)
                results[tracking_number] = result
            except Exception:
                _LOGGER.exception(
                    "Error tracking package %s via %s", tracking_number, carrier
                )
                # Retain previous data on failure
                if tracking_number in previous:
                    results[tracking_number] = previous[tracking_number]

        return results
