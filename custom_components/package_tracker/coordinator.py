"""DataUpdateCoordinator for Package Tracker."""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .carriers import get_provider
from .carriers.base import CarrierProvider, TrackingResult
from .const import (
    CONF_PACKAGES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SCAN_INTERVAL_JITTER,
    Carrier,
)

_LOGGER = logging.getLogger(__name__)


class PackageTrackerCoordinator(DataUpdateCoordinator[dict[str, TrackingResult]]):
    """Coordinator that scrapes carrier tracking pages for package updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._jittered_interval(),
        )
        self.entry = entry
        self._providers: dict[Carrier, CarrierProvider] = {}
        self._init_providers()

    @staticmethod
    def _jittered_interval() -> timedelta:
        """Return a randomized scan interval to avoid bot-like patterns."""
        jitter = random.randint(-SCAN_INTERVAL_JITTER, SCAN_INTERVAL_JITTER)
        return timedelta(seconds=DEFAULT_SCAN_INTERVAL + jitter)

    def _init_providers(self) -> None:
        """Initialize all carrier providers."""
        for carrier in Carrier:
            self._providers[carrier] = get_provider(carrier)

    def get_packages(self) -> list[dict[str, Any]]:
        """Return the list of tracked packages from options."""
        return list(self.entry.options.get(CONF_PACKAGES, []))

    async def _async_update_data(self) -> dict[str, TrackingResult]:
        """Fetch tracking data for all packages."""
        # Randomize interval for next poll
        self.update_interval = self._jittered_interval()

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
                if tracking_number in previous:
                    results[tracking_number] = previous[tracking_number]

        return results
