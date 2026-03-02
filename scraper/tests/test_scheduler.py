"""Tests for the background scheduler."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
def mock_browser():
    return AsyncMock()


@pytest.fixture
def scheduler(store, mock_browser):
    return Scheduler(store, mock_browser)


class TestRefreshPackage:
    @pytest.mark.asyncio
    async def test_refresh_scrapes_and_saves(self, scheduler, store):
        await store.add_package("TRACK1", "usps", "Pkg")

        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="TRACK1",
            status=TrackingStatus.DELIVERED,
            raw_status="Delivered",
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
