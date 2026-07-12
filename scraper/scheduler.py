"""Background scheduler for polling carriers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Browser

from .carriers import get_provider
from .const import DEFAULT_SCAN_INTERVAL, SCAN_INTERVAL_JITTER, Carrier
from .storage import PackageStore

_LOGGER = logging.getLogger(__name__)

_POLL_JOB_ID = "poll_all"


class Scheduler:
    """Polls all tracked packages on a jittered interval via APScheduler."""

    def __init__(self, store: PackageStore, camoufox: AsyncCamoufox, browser: Browser) -> None:
        self._store = store
        self._camoufox = camoufox
        self._browser = browser
        self._providers = {carrier: get_provider(carrier) for carrier in Carrier}
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Schedule the recurring poll and start the scheduler.

        The interval carries +/- ``SCAN_INTERVAL_JITTER`` seconds of randomness
        to avoid bot-like polling patterns, and fires once immediately on start.
        """
        self._scheduler.add_job(
            self._poll_all,
            trigger="interval",
            seconds=DEFAULT_SCAN_INTERVAL,
            jitter=SCAN_INTERVAL_JITTER,
            next_run_time=datetime.now(),
            id=_POLL_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        self._scheduler.start()
        _LOGGER.info("Scheduler started")

    async def stop(self) -> None:
        """Shut the scheduler down without waiting for a running poll."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            # AsyncIOScheduler defers the actual teardown onto the event loop,
            # so yield once to let the state settle before we return.
            await asyncio.sleep(0)
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
            await self._store.save_result(result)
        except Exception:
            elapsed = (datetime.now() - t0).total_seconds()
            _LOGGER.exception(
                "Error scraping %s for %s after %.1fs", carrier, tracking_number, elapsed
            )
