"""Tests for the background scheduler."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio

from scraper.carriers.base import TrackingResult
from scraper.const import Carrier, TrackingStatus
from scraper.scheduler import Scheduler
from scraper.storage import PackageStore


@pytest_asyncio.fixture
async def store():
    s = PackageStore(":memory:")
    await s.init_db()
    yield s
    await s.close()


@pytest.fixture
def mock_camoufox():
    camoufox = AsyncMock()
    camoufox.__aenter__ = AsyncMock()
    camoufox.__aexit__ = AsyncMock()
    return camoufox


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    # is_connected() is synchronous in Playwright — use MagicMock so the
    # return value is a plain bool, not a coroutine.
    browser.is_connected = MagicMock(return_value=True)
    return browser


@pytest.fixture
def scheduler(store, mock_camoufox, mock_browser):
    return Scheduler(store, mock_camoufox, mock_browser)


class TestRefreshPackage:
    @pytest.mark.asyncio
    async def test_refresh_scrapes_and_saves(self, scheduler, store):
        await store.add_package("TRACK1", "usps", "Pkg")

        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRACK1",
            status=TrackingStatus.DELIVERED,
            raw_status="Delivered",
            last_updated=datetime.now(),
        )

        with patch.object(
            scheduler._providers[Carrier.USPS],
            "async_track",
            return_value=mock_result,
        ):
            await scheduler.refresh_package("TRACK1")

        result = await store.get_tracking_result("TRACK1")
        assert result is not None
        assert result["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_refresh_nonexistent_package(self, scheduler):
        """Should log warning but not error."""
        await scheduler.refresh_package("NONEXISTENT")


class TestBrowserRestart:
    @pytest.mark.asyncio
    async def test_restart_browser_exits_and_relaunches(
        self, scheduler, mock_camoufox
    ):
        new_browser = AsyncMock()
        new_browser.is_connected.return_value = True
        mock_camoufox.__aenter__.return_value = new_browser

        await scheduler._restart_browser()

        mock_camoufox.__aexit__.assert_awaited_once_with(None, None, None)
        mock_camoufox.__aenter__.assert_awaited_once()
        assert scheduler._browser is new_browser

    @pytest.mark.asyncio
    async def test_disconnected_browser_restarts_before_scrape(
        self, scheduler, store, mock_camoufox, mock_browser
    ):
        mock_browser.is_connected.return_value = False
        new_browser = AsyncMock()
        new_browser.is_connected = MagicMock(return_value=True)
        mock_camoufox.__aenter__.return_value = new_browser

        await store.add_package("TRACK1", "usps", "Pkg")
        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRACK1",
            status=TrackingStatus.IN_TRANSIT,
            raw_status="In Transit",
            last_updated=datetime.now(),
        )

        with patch.object(
            scheduler._providers[Carrier.USPS],
            "async_track",
            new=AsyncMock(return_value=mock_result),
        ) as mock_track:
            await scheduler.refresh_package("TRACK1")

        mock_camoufox.__aenter__.assert_awaited_once()
        mock_track.assert_awaited_once_with("TRACK1", new_browser)

    @pytest.mark.asyncio
    async def test_restart_failure_skips_scrape(
        self, scheduler, store, mock_camoufox, mock_browser
    ):
        mock_browser.is_connected = MagicMock(return_value=False)
        mock_camoufox.__aexit__.side_effect = Exception("dead")
        mock_camoufox.__aenter__.side_effect = Exception("cannot start")

        await store.add_package("TRACK1", "usps", "Pkg")

        with patch.object(
            scheduler._providers[Carrier.USPS], "async_track"
        ) as mock_track:
            await scheduler.refresh_package("TRACK1")

        mock_track.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connected_browser_does_not_restart(
        self, scheduler, store, mock_camoufox, mock_browser
    ):
        mock_browser.is_connected.return_value = True

        await store.add_package("TRACK1", "usps", "Pkg")
        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRACK1",
            status=TrackingStatus.IN_TRANSIT,
            raw_status="In Transit",
            last_updated=datetime.now(),
        )

        with patch.object(
            scheduler._providers[Carrier.USPS], "async_track", return_value=mock_result
        ):
            await scheduler.refresh_package("TRACK1")

        mock_camoufox.__aenter__.assert_not_awaited()


class TestPollAll:
    @pytest.mark.asyncio
    async def test_skips_delivered_packages(self, scheduler, store):
        """Delivered packages should not be scraped during scheduled polling."""
        await store.add_package("DELIVERED1", "usps", "Done")
        await store.add_package("TRANSIT1", "usps", "Active")

        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="DELIVERED1",
            status=TrackingStatus.DELIVERED,
            raw_status="Delivered",
            last_updated=datetime.now(),
        )
        await store.save_tracking_result(
            tracking_number="DELIVERED1",
            status="delivered",
            raw_status="Delivered",
            estimated_delivery=None,
            last_updated=datetime.now().isoformat(),
            events_json="[]",
        )

        transit_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRANSIT1",
            status=TrackingStatus.IN_TRANSIT,
            raw_status="In Transit",
            last_updated=datetime.now(),
        )

        with patch.object(
            scheduler._providers[Carrier.USPS],
            "async_track",
            new=AsyncMock(return_value=transit_result),
        ) as mock_track:
            await scheduler._poll_all()

        mock_track.assert_awaited_once_with("TRANSIT1", scheduler._browser)

    @pytest.mark.asyncio
    async def test_skips_all_when_all_delivered(self, scheduler, store):
        """When all packages are delivered, async_track should never be called."""
        await store.add_package("DELIVERED1", "usps", "Done1")
        await store.add_package("DELIVERED2", "ups", "Done2")
        for tn in ("DELIVERED1", "DELIVERED2"):
            await store.save_tracking_result(
                tracking_number=tn,
                status="delivered",
                raw_status="Delivered",
                estimated_delivery=None,
                last_updated=datetime.now().isoformat(),
                events_json="[]",
            )

        with patch.object(
            scheduler._providers[Carrier.USPS], "async_track"
        ) as mock_usps, patch.object(
            scheduler._providers[Carrier.UPS], "async_track"
        ) as mock_ups:
            await scheduler._poll_all()

        mock_usps.assert_not_awaited()
        mock_ups.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_polls_all_when_none_delivered(self, scheduler, store):
        """All in-transit packages should be scraped."""
        await store.add_package("TRACK1", "usps", "Pkg1")
        await store.add_package("TRACK2", "usps", "Pkg2")

        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRACK1",
            status=TrackingStatus.IN_TRANSIT,
            raw_status="In Transit",
            last_updated=datetime.now(),
        )

        with patch.object(
            scheduler._providers[Carrier.USPS],
            "async_track",
            new=AsyncMock(return_value=mock_result),
        ) as mock_track:
            await scheduler._poll_all()

        assert mock_track.await_count == 2


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_creates_task(self, scheduler):
        scheduler.start()
        assert scheduler._task is not None
        assert not scheduler._task.done()
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, scheduler):
        scheduler.start()
        await scheduler.stop()
        assert scheduler._task.done()
