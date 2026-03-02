"""Tests for the FastAPI scraper routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from scraper.app import VERSION, app, store
from scraper.storage import PackageStore


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_store():
    """Use in-memory SQLite for API tests."""
    original_db_path = store._db_path
    store._db_path = ":memory:"
    await store.init_db()
    yield
    await store.close()
    store._db_path = original_db_path


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == VERSION


class TestPackagesEndpoints:
    @pytest.mark.asyncio
    async def test_get_packages_empty(self, client):
        resp = await client.get("/api/packages")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_add_package(self, client):
        resp = await client.post(
            "/api/packages",
            json={
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
                "label": "Test Package",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tracking_number"] == "92001234567890123456"
        assert data["carrier"] == "usps"
        assert data["label"] == "Test Package"
        assert data["tracking_url"] is not None

    @pytest.mark.asyncio
    async def test_add_duplicate_returns_409(self, client):
        await client.post(
            "/api/packages",
            json={
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
                "label": "Test",
            },
        )
        resp = await client.post(
            "/api/packages",
            json={
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
                "label": "Dup",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_packages_after_add(self, client):
        await client.post(
            "/api/packages",
            json={
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
                "label": "Test",
            },
        )
        resp = await client.get("/api/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["tracking_number"] == "92001234567890123456"

    @pytest.mark.asyncio
    async def test_remove_package(self, client):
        await client.post(
            "/api/packages",
            json={
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
                "label": "Test",
            },
        )
        resp = await client.delete("/api/packages/92001234567890123456")
        assert resp.status_code == 204

        resp = await client.get("/api/packages")
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_remove_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/packages/NONEXISTENT")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_refresh_without_scheduler_returns_503(self, client):
        """Refresh should fail when scheduler is not running."""
        import scraper.app as app_module

        original = app_module.scheduler
        app_module.scheduler = None
        try:
            resp = await client.post(
                "/api/packages/92001234567890123456/refresh"
            )
            assert resp.status_code == 503
        finally:
            app_module.scheduler = original
