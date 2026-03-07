"""Tests for the Package Tracker __init__ (setup, unload, service handler)."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import aiohttp

import pytest

from package_tracker import async_setup_entry, async_unload_entry
from package_tracker.api_client import ScraperApiError
from package_tracker.const import CONF_PACKAGES, CONF_SCRAPER_URL, DOMAIN
from homeassistant.exceptions import HomeAssistantError


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_SCRAPER_URL: "http://localhost:8230"}
    entry.options = {CONF_PACKAGES: []}
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    return entry


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    coord._ensure_client = MagicMock(return_value=AsyncMock())
    return coord


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.services = MagicMock()
    hass.services.has_service.return_value = False
    hass.http = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_update_entry = MagicMock()
    return hass


async def _setup_entry(mock_hass, mock_entry, mock_coordinator):
    """Call async_setup_entry with all external deps patched. Returns registered service handler."""
    mock_hass.data = {DOMAIN: {}}
    mock_hass.services = MagicMock()
    mock_hass.services.has_service.return_value = False

    with patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coordinator):
        await async_setup_entry(mock_hass, mock_entry)

    handler = mock_hass.services.async_register.call_args[0][2]
    return handler


@pytest.mark.asyncio
async def test_service_registered_on_setup(mock_hass, mock_entry, mock_coordinator):
    await _setup_entry(mock_hass, mock_entry, mock_coordinator)
    mock_hass.services.async_register.assert_called_once_with(
        DOMAIN, "add_package", ANY, schema=ANY
    )


@pytest.mark.asyncio
async def test_service_not_registered_twice(mock_hass, mock_entry, mock_coordinator):
    mock_hass.services.has_service.return_value = True
    with patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coordinator):
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        await async_setup_entry(mock_hass, mock_entry)
    mock_hass.services.async_register.assert_not_called()


@pytest.mark.asyncio
async def test_service_removed_on_last_entry_unload(mock_hass, mock_entry):
    mock_hass.data = {DOMAIN: {mock_entry.entry_id: MagicMock()}}
    mock_hass.services = MagicMock()
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    await async_unload_entry(mock_hass, mock_entry)

    mock_hass.services.async_remove.assert_called_once_with(DOMAIN, "add_package")
    assert mock_entry.entry_id not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_service_not_removed_when_other_entries_remain(mock_hass, mock_entry):
    other_coord = MagicMock()
    mock_hass.data = {DOMAIN: {mock_entry.entry_id: MagicMock(), "other": other_coord}}
    mock_hass.services = MagicMock()
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    await async_unload_entry(mock_hass, mock_entry)

    mock_hass.services.async_remove.assert_not_called()


@pytest.mark.asyncio
async def test_handler_reuses_coordinator_client(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: []}

    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)
    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "Test", "carrier": "ups"}

    with patch("aiohttp.ClientSession") as mock_session:
        await handler(call)
        mock_session.assert_not_called()

    mock_coordinator._ensure_client.assert_called_once()
    mock_client.async_add_package.assert_called_once_with("1Z12345E6605272234", "ups", "Test")


@pytest.mark.asyncio
async def test_handler_auto_detects_carrier(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "9400111899223397471677", "label": "Test", "carrier": ""}

    with patch("package_tracker.detect_carrier") as mock_detect:
        mock_detect.return_value = MagicMock(value="usps")
        await handler(call)
        mock_detect.assert_called_once_with("9400111899223397471677")

    mock_client.async_add_package.assert_called_once_with("9400111899223397471677", "usps", "Test")


@pytest.mark.asyncio
async def test_handler_raises_on_undetectable_carrier(mock_hass, mock_entry, mock_coordinator):
    mock_coordinator._ensure_client = MagicMock(return_value=AsyncMock())
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "INVALID123", "label": "Test", "carrier": ""}

    with patch("package_tracker.detect_carrier", return_value=None):
        with pytest.raises(HomeAssistantError, match="Cannot auto-detect carrier"):
            await handler(call)


@pytest.mark.asyncio
async def test_handler_raises_on_duplicate(mock_hass, mock_entry, mock_coordinator):
    mock_coordinator._ensure_client = MagicMock(return_value=AsyncMock())
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: [{"tracking_number": "1Z999AA10123456784", "label": "x", "carrier": "ups"}]}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z999AA10123456784", "label": "Dupe", "carrier": "ups"}

    with pytest.raises(HomeAssistantError, match="already being tracked"):
        await handler(call)


@pytest.mark.asyncio
async def test_handler_raises_on_scraper_error(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_add_package.side_effect = ScraperApiError("timeout")
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "Test", "carrier": "ups"}

    with pytest.raises(HomeAssistantError, match="Scraper error"):
        await handler(call)


@pytest.mark.asyncio
async def test_handler_calls_refresh_after_add(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_coordinator.data = {}
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "Test", "carrier": "ups"}
    await handler(call)

    mock_client.async_refresh_package.assert_called_once_with("1Z12345E6605272234")


@pytest.mark.asyncio
async def test_handler_updates_coordinator_data_on_refresh(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_refresh_package.return_value = {
        "tracking_number": "1Z12345E6605272234",
        "carrier": "ups",
        "status": "in_transit",
        "raw_status": "In Transit",
        "estimated_delivery": None,
        "last_updated": None,
        "events": [],
        "tracking_url": "https://www.ups.com/track?tracknum=1Z12345E6605272234",
    }
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_coordinator.data = {}
    mock_coordinator.async_set_updated_data = MagicMock()
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "Test", "carrier": "ups"}
    await handler(call)

    mock_coordinator.async_set_updated_data.assert_called_once()
    updated_data = mock_coordinator.async_set_updated_data.call_args[0][0]
    assert "1Z12345E6605272234" in updated_data


@pytest.mark.asyncio
async def test_handler_continues_if_refresh_fails(mock_hass, mock_entry, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_refresh_package.side_effect = ScraperApiError("timeout")
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.entry = mock_entry
    mock_coordinator.data = {}
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "Test", "carrier": "ups"}
    # Should not raise — refresh failure is swallowed
    await handler(call)

    mock_hass.config_entries.async_update_entry.assert_called_once()


@pytest.mark.asyncio
async def test_handler_updates_options_on_success(mock_hass, mock_entry, mock_coordinator):
    mock_coordinator._ensure_client = MagicMock(return_value=AsyncMock())
    mock_coordinator.entry = mock_entry
    mock_entry.options = {CONF_PACKAGES: []}
    handler = await _setup_entry(mock_hass, mock_entry, mock_coordinator)

    call = MagicMock()
    call.data = {"tracking_number": "1Z12345E6605272234", "label": "My Order", "carrier": "ups"}
    await handler(call)

    mock_hass.config_entries.async_update_entry.assert_called_once()
    updated_options = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
    assert {"tracking_number": "1Z12345E6605272234", "label": "My Order", "carrier": "ups"} in updated_options[CONF_PACKAGES]
