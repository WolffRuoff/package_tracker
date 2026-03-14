"""Common test fixtures for Package Tracker."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.carriers.base import TrackingEvent, TrackingResult
from package_tracker.const import (
    CONF_PACKAGES,
    CONF_SCRAPER_URL,
    DOMAIN,
    Carrier,
    TrackingStatus,
)


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Return a mock ConfigEntry with scraper URL."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_SCRAPER_URL: "http://localhost:8230"}
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


@pytest.fixture
def mock_scraper_api():
    """Mock the ScraperApiClient for tests.

    Returns a mock client instance that can be configured by tests.
    """
    mock_client = AsyncMock()

    # Default: health check passes
    mock_client.async_health.return_value = {"status": "ok", "version": "2.0.0"}

    # Default: return one package
    mock_client.async_get_packages.return_value = [
        {
            "tracking_number": "92001234567890123456",
            "carrier": "usps",
            "label": "Test Package",
            "created_at": "2025-01-15T00:00:00+00:00",
            "status": "delivered",
            "raw_status": "Delivered",
            "estimated_delivery": "2025-01-15T00:00:00",
            "last_updated": "2025-01-15T14:30:00",
            "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=92001234567890123456",
            "events": [
                {
                    "timestamp": "2025-01-15T14:30:00",
                    "location": "Springfield, IL",
                    "description": "Delivered",
                    "status": "delivered",
                },
            ],
        }
    ]

    # Default: add package succeeds
    mock_client.async_add_package.return_value = {
        "tracking_number": "TEST",
        "carrier": "usps",
        "label": "Test",
        "created_at": "2025-01-15T00:00:00+00:00",
    }

    # Default: remove package succeeds
    mock_client.async_remove_package.return_value = None

    # Default: carriers list
    mock_client.async_get_carriers.return_value = [
        {"id": "usps", "name": "USPS"},
        {"id": "ups", "name": "UPS"},
        {"id": "fedex", "name": "FedEx"},
        {"id": "speedx", "name": "SpeedX"},
    ]

    return mock_client
