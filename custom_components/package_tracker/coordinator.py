"""DataUpdateCoordinator for Package Tracker."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_client import ScraperApiClient, ScraperApiError
from .carriers.base import TrackingEvent, TrackingResult
from .const import (
    CONF_AUTO_REMOVE_DAYS,
    CONF_PACKAGES,
    DEFAULT_AUTO_REMOVE_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SCAN_INTERVAL_JITTER,
    Carrier,
    TrackingStatus,
)

_LOGGER = logging.getLogger(__name__)


class PackageTrackerCoordinator(DataUpdateCoordinator[dict[str, TrackingResult]]):
    """Coordinator that polls the scraper API for package updates."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, scraper_url: str
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._jittered_interval(),
        )
        self.entry = entry
        self._scraper_url = scraper_url
        self._session: aiohttp.ClientSession | None = None
        self._client: ScraperApiClient | None = None

    @staticmethod
    def _jittered_interval() -> timedelta:
        """Return a randomized scan interval to avoid bot-like patterns."""
        jitter = random.randint(-SCAN_INTERVAL_JITTER, SCAN_INTERVAL_JITTER)
        return timedelta(seconds=DEFAULT_SCAN_INTERVAL + jitter)

    def _ensure_client(self) -> ScraperApiClient:
        """Lazily create the HTTP session and API client."""
        if self._client is None:
            self._session = aiohttp.ClientSession()
            self._client = ScraperApiClient(self._scraper_url, self._session)
        return self._client

    def get_packages(self) -> list[dict[str, Any]]:
        """Return the list of tracked packages from options."""
        return list(self.entry.options.get(CONF_PACKAGES, []))

    async def _async_update_data(self) -> dict[str, TrackingResult]:
        """Fetch tracking data from the scraper API."""
        # Randomize interval for next poll
        self.update_interval = self._jittered_interval()

        previous = self.data or {}

        client = self._ensure_client()

        try:
            packages_data = await client.async_get_packages()
        except ScraperApiError:
            _LOGGER.exception("Error fetching packages from scraper")
            return previous

        results: dict[str, TrackingResult] = {}

        for pkg in packages_data:
            tracking_number = pkg["tracking_number"]

            events = []
            for e in pkg.get("events", []):
                try:
                    events.append(
                        TrackingEvent(
                            timestamp=datetime.fromisoformat(e["timestamp"]),
                            location=e["location"],
                            description=e["description"],
                            status=TrackingStatus(e["status"]),
                        )
                    )
                except (ValueError, KeyError):
                    continue

            try:
                result = TrackingResult(
                    carrier=Carrier(pkg["carrier"]),
                    tracking_number=tracking_number,
                    status=TrackingStatus(pkg.get("status", "unknown")),
                    raw_status=pkg.get("raw_status", ""),
                    estimated_delivery=(
                        datetime.fromisoformat(pkg["estimated_delivery"])
                        if pkg.get("estimated_delivery")
                        else None
                    ),
                    last_updated=(
                        datetime.fromisoformat(pkg["last_updated"])
                        if pkg.get("last_updated")
                        else None
                    ),
                    events=events,
                    tracking_url=pkg.get("tracking_url"),
                )
                results[tracking_number] = result
            except (ValueError, KeyError):
                _LOGGER.exception(
                    "Error parsing tracking result for %s", tracking_number
                )
                if tracking_number in previous:
                    results[tracking_number] = previous[tracking_number]

        await self._async_process_delivered_packages(results)

        return results

    async def _async_process_delivered_packages(
        self, results: dict[str, TrackingResult]
    ) -> None:
        """Stamp delivered_at on newly delivered packages and remove expired ones."""
        packages = list(self.entry.options.get(CONF_PACKAGES, []))
        auto_remove_days = self.entry.options.get(
            CONF_AUTO_REMOVE_DAYS, DEFAULT_AUTO_REMOVE_DAYS
        )
        now = datetime.now(timezone.utc)
        changed = False

        updated_packages = []
        for pkg in packages:
            tracking_number = pkg["tracking_number"]
            result = results.get(tracking_number)

            # Stamp delivered_at when first observed as DELIVERED
            if (
                result
                and result.status == TrackingStatus.DELIVERED
                and "delivered_at" not in pkg
            ):
                pkg = {**pkg, "delivered_at": now.isoformat()}
                changed = True

            # Remove if past threshold
            if auto_remove_days > 0 and "delivered_at" in pkg:
                delivered_at = datetime.fromisoformat(pkg["delivered_at"])
                if now - delivered_at >= timedelta(days=auto_remove_days):
                    changed = True
                    continue  # skip adding to updated list

            updated_packages.append(pkg)

        if changed:
            new_options = {**self.entry.options, CONF_PACKAGES: updated_packages}
            self.hass.config_entries.async_update_entry(
                self.entry, options=new_options
            )

    async def async_shutdown(self) -> None:
        """Close the HTTP session on shutdown."""
        if self._session:
            await self._session.close()
            self._session = None
            self._client = None
        await super().async_shutdown()
