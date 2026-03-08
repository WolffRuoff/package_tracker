"""Common test fixtures for the scraper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from scraper.storage import PackageStore

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- HTML fixture loaders ---


@pytest.fixture
def usps_delivered_html():
    return (FIXTURES_DIR / "usps" / "delivered.html").read_text()


@pytest.fixture
def usps_in_transit_html():
    return (FIXTURES_DIR / "usps" / "in_transit.html").read_text()


@pytest.fixture
def usps_not_found_html():
    return (FIXTURES_DIR / "usps" / "not_found.html").read_text()


@pytest.fixture
def ups_delivered_html():
    return (FIXTURES_DIR / "ups" / "delivered.html").read_text()


@pytest.fixture
def ups_in_transit_html():
    return (FIXTURES_DIR / "ups" / "in_transit.html").read_text()


@pytest.fixture
def ups_not_found_html():
    return (FIXTURES_DIR / "ups" / "not_found.html").read_text()


@pytest.fixture
def fedex_delivered_html():
    return (FIXTURES_DIR / "fedex" / "delivered.html").read_text()


@pytest.fixture
def fedex_in_transit_html():
    return (FIXTURES_DIR / "fedex" / "in_transit.html").read_text()


@pytest.fixture
def fedex_not_found_html():
    return (FIXTURES_DIR / "fedex" / "not_found.html").read_text()


@pytest.fixture
def speedx_delivered_html():
    return (FIXTURES_DIR / "speedx" / "delivered.html").read_text()


@pytest.fixture
def speedx_in_transit_html():
    return (FIXTURES_DIR / "speedx" / "in_transit.html").read_text()


@pytest.fixture
def speedx_order_placed_html():
    return (FIXTURES_DIR / "speedx" / "order_placed.html").read_text()


@pytest.fixture
def mock_browser():
    """Mock Playwright browser for carrier tests."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html></html>")
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="")
    mock_page.on = MagicMock()  # page.on() is synchronous in Playwright

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_context)

    return browser, mock_page


@pytest_asyncio.fixture
async def in_memory_store():
    """Return a PackageStore backed by in-memory SQLite."""
    store = PackageStore(":memory:")
    await store.init_db()
    yield store
    await store.close()
