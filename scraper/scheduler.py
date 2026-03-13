"""Background scheduler for polling carriers."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime

from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Browser

from .carriers import get_provider
from .carriers.base import TrackingResult
from .const import DEFAULT_SCAN_INTERVAL, SCAN_INTERVAL_JITTER, Carrier
from .storage import PackageStore

_LOGGER = logging.getLogger(__name__)


class Scheduler:
    """Background task that polls all tracked packages on an interval."""

    def __init__(self, store: PackageStore, camoufox: AsyncCamoufox, browser: Browser) -> None:
        self._store = store
        self._camoufox = camoufox
        self._browser = browser
        self._task: asyncio.Task | None = None
        self._providers = {carrier: get_provider(carrier) for carrier in Carrier}

    def start(self) -> None:
        """Start the background polling loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
            _LOGGER.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the background polling loop."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            _LOGGER.info("Scheduler stopped")

    async def _restart_browser(self) -> None:
        """Restart the Camoufox browser after a crash."""
        _LOGGER.warning("Browser is closed; restarting Camoufox")
        try:
            await self._camoufox.__aexit__(None, None, None)
        except Exception:
            pass
        self._browser = await self._camoufox.__aenter__()
        _LOGGER.info("Camoufox browser restarted successfully")

    async def refresh_package(self, tracking_number: str) -> None:
        """Force an immediate re-scrape of a single package."""
        packages = await self._store.get_all_packages()
        pkg = next(
            (p for p in packages if p["tracking_number"] == tracking_number), None
        )
        if pkg is None:
            _LOGGER.warning("Package %s not found for refresh", tracking_number)
            return
        await self._scrape_package(pkg)

    async def _run(self) -> None:
        """Main polling loop."""
        while True:
            try:
                await self._poll_all()
            except Exception:
                _LOGGER.exception("Error during scheduled poll")

            jitter = random.randint(-SCAN_INTERVAL_JITTER, SCAN_INTERVAL_JITTER)
            interval = DEFAULT_SCAN_INTERVAL + jitter
            _LOGGER.debug("Next poll in %d seconds", interval)
            await asyncio.sleep(interval)

    async def _poll_all(self) -> None:
        """Poll all tracked packages."""
        packages = await self._store.get_all_packages()
        pending = [p for p in packages if p.get("status") != "delivered"]
        _LOGGER.info(
            "Polling %d/%d packages (skipping %d delivered)",
            len(pending),
            len(packages),
            len(packages) - len(pending),
        )
        for pkg in pending:
            await self._scrape_package(pkg)

    async def _scrape_package(self, pkg: dict) -> None:
        """Scrape tracking data for a single package."""
        tracking_number = pkg["tracking_number"]
        carrier = Carrier(pkg["carrier"])
        provider = self._providers.get(carrier)

        if provider is None:
            _LOGGER.warning("No provider for carrier %s", carrier)
            return

        if not self._browser.is_connected():
            try:
                await self._restart_browser()
            except Exception:
                _LOGGER.exception(
                    "Failed to restart browser; skipping %s %s", carrier, tracking_number
                )
                return

        t0 = datetime.now()
        try:
            result = await provider.async_track(tracking_number, self._browser)
            elapsed = (datetime.now() - t0).total_seconds()
            _LOGGER.info(
                "Scraped %s %s in %.1fs: status=%s raw_status=%r estimated_delivery=%s events=%d",
                carrier.value,
                tracking_number,
                elapsed,
                result.status.value,
                result.raw_status,
                result.estimated_delivery,
                len(result.events),
            )
            await self._save_result(result)
        except Exception:
            elapsed = (datetime.now() - t0).total_seconds()
            _LOGGER.exception(
                "Error scraping %s for %s after %.1fs", carrier, tracking_number, elapsed
            )

    async def _save_result(self, result: TrackingResult) -> None:
        """Persist a tracking result to the database."""
        events_json = json.dumps(
            [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "location": e.location,
                    "description": e.description,
                    "status": e.status.value,
                }
                for e in result.events
            ]
        )
        await self._store.save_tracking_result(
            tracking_number=result.tracking_number,
            status=result.status.value,
            raw_status=result.raw_status,
            estimated_delivery=(
                result.estimated_delivery.isoformat()
                if result.estimated_delivery
                else None
            ),
            last_updated=(
                result.last_updated.isoformat() if result.last_updated else None
            ),
            events_json=events_json,
        )
