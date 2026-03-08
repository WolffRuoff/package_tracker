"""Tests for Package Tracker __init__ (setup/unload orchestration)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker import async_setup_entry, async_unload_entry
from package_tracker.const import CONF_SCRAPER_URL, DOMAIN


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_SCRAPER_URL: "http://localhost:8230"}
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    return entry


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    return coord


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.services = MagicMock()
    hass.http = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.mark.asyncio
async def test_service_registered_on_setup(mock_hass, mock_entry, mock_coordinator):
    with (
        patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coordinator),
        patch("package_tracker.register_services") as mock_register,
    ):
        await async_setup_entry(mock_hass, mock_entry)
    mock_register.assert_called_once_with(mock_hass)


@pytest.mark.asyncio
async def test_service_not_registered_twice(mock_hass, mock_entry, mock_coordinator):
    """register_services is always called; idempotency is handled inside it."""
    with (
        patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coordinator),
        patch("package_tracker.register_services") as mock_register,
    ):
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        await async_setup_entry(mock_hass, mock_entry)
        await async_setup_entry(mock_hass, mock_entry)
    assert mock_register.call_count == 2


@pytest.mark.asyncio
async def test_service_removed_on_last_entry_unload(mock_hass, mock_entry):
    mock_hass.data = {DOMAIN: {mock_entry.entry_id: MagicMock()}}

    with patch("package_tracker.unregister_services") as mock_unregister:
        await async_unload_entry(mock_hass, mock_entry)

    mock_unregister.assert_called_once_with(mock_hass)
    assert mock_entry.entry_id not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_service_not_removed_when_other_entries_remain(mock_hass, mock_entry):
    mock_hass.data = {DOMAIN: {mock_entry.entry_id: MagicMock(), "other": MagicMock()}}

    with patch("package_tracker.unregister_services") as mock_unregister:
        await async_unload_entry(mock_hass, mock_entry)

    mock_unregister.assert_not_called()
