"""Tests for the PackageStore (SQLite storage)."""

from __future__ import annotations

import json

import pytest

from scraper.const import TrackingStatus


class TestInitDb:
    @pytest.mark.asyncio
    async def test_creates_tables(self, in_memory_store):
        """Tables should exist after init_db."""
        cursor = await in_memory_store._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in await cursor.fetchall()]
        assert "packages" in tables
        assert "tracking_results" in tables


class TestAddPackage:
    @pytest.mark.asyncio
    async def test_add_package(self, in_memory_store):
        pkg = await in_memory_store.add_package("TRACK123", "usps", "My Package")
        assert pkg is not None
        assert pkg["tracking_number"] == "TRACK123"
        assert pkg["carrier"] == "usps"
        assert pkg["label"] == "My Package"
        assert "created_at" in pkg

    @pytest.mark.asyncio
    async def test_add_duplicate_returns_none(self, in_memory_store):
        await in_memory_store.add_package("TRACK123", "usps", "First")
        result = await in_memory_store.add_package("TRACK123", "usps", "Duplicate")
        assert result is None


class TestRemovePackage:
    @pytest.mark.asyncio
    async def test_remove_existing(self, in_memory_store):
        await in_memory_store.add_package("TRACK123", "usps", "Pkg")
        removed = await in_memory_store.remove_package("TRACK123")
        assert removed is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, in_memory_store):
        removed = await in_memory_store.remove_package("NONEXISTENT")
        assert removed is False

    @pytest.mark.asyncio
    async def test_remove_cascades_to_results(self, in_memory_store):
        """Removing a package should also remove its tracking result."""
        await in_memory_store.add_package("TRACK123", "usps", "Pkg")
        await in_memory_store.save_tracking_result(
            "TRACK123", "delivered", "Delivered", None, None, "[]"
        )
        await in_memory_store.remove_package("TRACK123")
        result = await in_memory_store.get_tracking_result("TRACK123")
        assert result is None


class TestGetAllPackages:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, in_memory_store):
        packages = await in_memory_store.get_all_packages()
        assert packages == []

    @pytest.mark.asyncio
    async def test_returns_packages_with_results(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "Pkg1")
        await in_memory_store.save_tracking_result(
            "TRACK1", "delivered", "Delivered", None, "2025-01-15T14:30:00", "[]"
        )
        packages = await in_memory_store.get_all_packages()
        assert len(packages) == 1
        assert packages[0]["tracking_number"] == "TRACK1"
        assert packages[0]["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_returns_unknown_status_without_result(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "Pkg1")
        packages = await in_memory_store.get_all_packages()
        assert len(packages) == 1
        assert packages[0]["status"] == TrackingStatus.UNKNOWN


class TestGetPackage:
    @pytest.mark.asyncio
    async def test_get_package_returns_none_for_unknown(self, in_memory_store):
        result = await in_memory_store.get_package("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_package_returns_package_without_tracking_result(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "My Pkg")
        pkg = await in_memory_store.get_package("TRACK1")
        assert pkg is not None
        assert pkg["tracking_number"] == "TRACK1"
        assert pkg["carrier"] == "usps"
        assert pkg["label"] == "My Pkg"
        assert pkg["status"] == TrackingStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_package_returns_package_with_tracking_result(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "My Pkg")
        await in_memory_store.save_tracking_result(
            "TRACK1", "delivered", "Delivered", None, "2025-01-15T14:30:00", "[]"
        )
        pkg = await in_memory_store.get_package("TRACK1")
        assert pkg is not None
        assert pkg["status"] == "delivered"
        assert pkg["raw_status"] == "Delivered"
        assert pkg["last_updated"] == "2025-01-15T14:30:00"


class TestSaveTrackingResult:
    @pytest.mark.asyncio
    async def test_save_and_retrieve(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "Pkg1")
        events = json.dumps([{"timestamp": "2025-01-15T14:30:00", "location": "IL", "description": "Delivered", "status": "delivered"}])
        await in_memory_store.save_tracking_result(
            "TRACK1", "delivered", "Delivered", "2025-01-15T00:00:00", "2025-01-15T14:30:00", events
        )
        result = await in_memory_store.get_tracking_result("TRACK1")
        assert result is not None
        assert result["status"] == "delivered"
        assert result["raw_status"] == "Delivered"
        assert result["events_json"] == events

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, in_memory_store):
        await in_memory_store.add_package("TRACK1", "usps", "Pkg1")
        await in_memory_store.save_tracking_result(
            "TRACK1", "in_transit", "In Transit", None, None, "[]"
        )
        await in_memory_store.save_tracking_result(
            "TRACK1", "delivered", "Delivered", None, None, "[]"
        )
        result = await in_memory_store.get_tracking_result("TRACK1")
        assert result["status"] == "delivered"
