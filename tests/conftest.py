"""Common test fixtures for Package Tracker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from package_tracker.const import (
    CONF_PACKAGES,
    DOMAIN,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Return a mock ConfigEntry (no API keys needed)."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {}
    entry.options = {
        CONF_PACKAGES: [
            {
                "label": "Test Package",
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
            }
        ]
    }
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    return entry


# --- HTML fixture loaders ---


@pytest.fixture
def usps_delivered_html():
    """Return rendered HTML of a USPS delivered tracking page."""
    return (FIXTURES_DIR / "usps" / "delivered.html").read_text()


@pytest.fixture
def usps_in_transit_html():
    """Return rendered HTML of a USPS in-transit tracking page."""
    return (FIXTURES_DIR / "usps" / "in_transit.html").read_text()


@pytest.fixture
def usps_not_found_html():
    """Return rendered HTML of a USPS not-found tracking page."""
    return (FIXTURES_DIR / "usps" / "not_found.html").read_text()


@pytest.fixture
def ups_delivered_html():
    """Return rendered HTML of a UPS delivered tracking page."""
    return (FIXTURES_DIR / "ups" / "delivered.html").read_text()


@pytest.fixture
def ups_in_transit_html():
    """Return rendered HTML of a UPS in-transit tracking page."""
    return (FIXTURES_DIR / "ups" / "in_transit.html").read_text()


@pytest.fixture
def ups_not_found_html():
    """Return rendered HTML of a UPS not-found tracking page."""
    return (FIXTURES_DIR / "ups" / "not_found.html").read_text()


@pytest.fixture
def fedex_delivered_html():
    """Return rendered HTML of a FedEx delivered tracking page."""
    return (FIXTURES_DIR / "fedex" / "delivered.html").read_text()


@pytest.fixture
def fedex_in_transit_html():
    """Return rendered HTML of a FedEx in-transit tracking page."""
    return (FIXTURES_DIR / "fedex" / "in_transit.html").read_text()


@pytest.fixture
def fedex_not_found_html():
    """Return rendered HTML of a FedEx not-found tracking page."""
    return (FIXTURES_DIR / "fedex" / "not_found.html").read_text()


@pytest.fixture
def mock_playwright():
    """Mock Playwright to avoid real browser launches.

    Returns (mock_playwright_context, mock_page) so tests can configure
    mock_page.content.return_value with fixture HTML.
    """
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html></html>")

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm, mock_page
