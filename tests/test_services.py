"""Tests for Package Tracker service handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.api_client import ScraperApiError
from package_tracker.const import CONF_PACKAGES, DOMAIN
from package_tracker.services import handle_add_package, handle_refresh_packages
from homeassistant.exceptions import HomeAssistantError


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.options = {CONF_PACKAGES: []}
    return entry


@pytest.fixture
def mock_coordinator(mock_entry):
    coord = MagicMock()
    coord.entry = mock_entry
    coord.data = {}
    coord._ensure_client = MagicMock(return_value=AsyncMock())
    coord.async_set_updated_data = MagicMock()
    return coord


@pytest.fixture
def mock_hass(mock_coordinator):
    hass = MagicMock()
    hass.data = {DOMAIN: {"test_entry_id": mock_coordinator}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


def _make_call(**data):
    call = MagicMock()
    call.data = data
    return call


# --- add_package handler tests ---


@pytest.mark.asyncio
async def test_add_reuses_coordinator_client(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)

    call = _make_call(tracking_number="1Z12345E6605272234", label="Test", carrier="ups")

    with patch("aiohttp.ClientSession") as mock_session:
        await handle_add_package(mock_hass, call)
        mock_session.assert_not_called()

    mock_coordinator._ensure_client.assert_called()
    mock_client.async_add_package.assert_called_once_with("1Z12345E6605272234", "ups", "Test")


@pytest.mark.asyncio
async def test_add_auto_detects_carrier(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)

    call = _make_call(tracking_number="9400111899223397471677", label="Test", carrier="")

    with patch("package_tracker.services.detect_carrier") as mock_detect:
        mock_detect.return_value = MagicMock(value="usps")
        await handle_add_package(mock_hass, call)
        mock_detect.assert_called_once_with("9400111899223397471677")

    mock_client.async_add_package.assert_called_once_with("9400111899223397471677", "usps", "Test")


@pytest.mark.asyncio
async def test_add_raises_on_undetectable_carrier(mock_hass, mock_coordinator):
    call = _make_call(tracking_number="INVALID123", label="Test", carrier="")

    with patch("package_tracker.services.detect_carrier", return_value=None):
        with pytest.raises(HomeAssistantError, match="Cannot auto-detect carrier"):
            await handle_add_package(mock_hass, call)


@pytest.mark.asyncio
async def test_add_raises_on_duplicate(mock_hass, mock_coordinator, mock_entry):
    mock_entry.options = {CONF_PACKAGES: [{"tracking_number": "1Z999AA10123456784", "label": "x", "carrier": "ups"}]}

    call = _make_call(tracking_number="1Z999AA10123456784", label="Dupe", carrier="ups")

    with pytest.raises(HomeAssistantError, match="already being tracked"):
        await handle_add_package(mock_hass, call)


@pytest.mark.asyncio
async def test_add_raises_on_scraper_error(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_add_package.side_effect = ScraperApiError("timeout")
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)

    call = _make_call(tracking_number="1Z12345E6605272234", label="Test", carrier="ups")

    with pytest.raises(HomeAssistantError, match="Scraper error"):
        await handle_add_package(mock_hass, call)


@pytest.mark.asyncio
async def test_add_calls_refresh_after_add(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)

    call = _make_call(tracking_number="1Z12345E6605272234", label="Test", carrier="ups")
    await handle_add_package(mock_hass, call)

    mock_client.async_refresh_package.assert_called_once_with("1Z12345E6605272234")


@pytest.mark.asyncio
async def test_add_updates_coordinator_data_on_refresh(mock_hass, mock_coordinator):
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

    call = _make_call(tracking_number="1Z12345E6605272234", label="Test", carrier="ups")
    await handle_add_package(mock_hass, call)

    mock_coordinator.async_set_updated_data.assert_called_once()
    updated_data = mock_coordinator.async_set_updated_data.call_args[0][0]
    assert "1Z12345E6605272234" in updated_data


@pytest.mark.asyncio
async def test_add_continues_if_refresh_fails(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_refresh_package.side_effect = ScraperApiError("timeout")
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)

    call = _make_call(tracking_number="1Z12345E6605272234", label="Test", carrier="ups")
    # Should not raise — refresh failure is swallowed
    await handle_add_package(mock_hass, call)

    mock_hass.config_entries.async_update_entry.assert_called_once()


@pytest.mark.asyncio
async def test_add_updates_options_on_success(mock_hass, mock_coordinator):
    call = _make_call(tracking_number="1Z12345E6605272234", label="My Order", carrier="ups")
    await handle_add_package(mock_hass, call)

    mock_hass.config_entries.async_update_entry.assert_called_once()
    updated_options = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
    assert {"tracking_number": "1Z12345E6605272234", "label": "My Order", "carrier": "ups"} in updated_options[CONF_PACKAGES]


# --- refresh_packages handler tests ---


@pytest.mark.asyncio
async def test_refresh_refreshes_all_packages(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_client.async_refresh_package.side_effect = [
        {
            "tracking_number": "1Z111",
            "carrier": "ups",
            "status": "in_transit",
            "raw_status": "In Transit",
            "estimated_delivery": None,
            "last_updated": None,
            "events": [],
            "tracking_url": "https://ups.com/track?tracknum=1Z111",
        },
        {
            "tracking_number": "9400222",
            "carrier": "usps",
            "status": "delivered",
            "raw_status": "Delivered",
            "estimated_delivery": None,
            "last_updated": None,
            "events": [],
            "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400222",
        },
    ]
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.data = {"1Z111": MagicMock(), "9400222": MagicMock()}

    call = _make_call()
    await handle_refresh_packages(mock_hass, call)

    assert mock_client.async_refresh_package.call_count == 2
    mock_coordinator.async_set_updated_data.assert_called_once()
    updated_data = mock_coordinator.async_set_updated_data.call_args[0][0]
    assert "1Z111" in updated_data
    assert "9400222" in updated_data


@pytest.mark.asyncio
async def test_refresh_continues_on_partial_failure(mock_hass, mock_coordinator):
    existing_1z = MagicMock()
    mock_client = AsyncMock()
    mock_client.async_refresh_package.side_effect = [
        ScraperApiError("timeout"),
        {
            "tracking_number": "9400222",
            "carrier": "usps",
            "status": "delivered",
            "raw_status": "Delivered",
            "estimated_delivery": None,
            "last_updated": None,
            "events": [],
            "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400222",
        },
    ]
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.data = {"1Z111": existing_1z, "9400222": MagicMock()}

    call = _make_call()
    await handle_refresh_packages(mock_hass, call)

    assert mock_client.async_refresh_package.call_count == 2
    mock_coordinator.async_set_updated_data.assert_called_once()
    updated_data = mock_coordinator.async_set_updated_data.call_args[0][0]
    assert updated_data["1Z111"] is existing_1z
    assert "9400222" in updated_data


@pytest.mark.asyncio
async def test_refresh_skips_delivered_packages(mock_hass, mock_coordinator):
    from package_tracker.const import TrackingStatus

    delivered = MagicMock()
    delivered.status = TrackingStatus.DELIVERED
    in_transit = MagicMock()
    in_transit.status = TrackingStatus.IN_TRANSIT

    mock_client = AsyncMock()
    mock_client.async_refresh_package.return_value = {
        "tracking_number": "1Z111",
        "carrier": "ups",
        "status": "in_transit",
        "raw_status": "In Transit",
        "estimated_delivery": None,
        "last_updated": None,
        "events": [],
        "tracking_url": "https://ups.com/track?tracknum=1Z111",
    }
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.data = {"1Z111": in_transit, "9400222": delivered}

    await handle_refresh_packages(mock_hass, _make_call())

    # Only the in-transit package is re-scraped; delivered is left untouched.
    mock_client.async_refresh_package.assert_called_once_with("1Z111")
    updated_data = mock_coordinator.async_set_updated_data.call_args[0][0]
    assert updated_data["9400222"] is delivered


@pytest.mark.asyncio
async def test_refresh_no_packages(mock_hass, mock_coordinator):
    mock_client = AsyncMock()
    mock_coordinator._ensure_client = MagicMock(return_value=mock_client)
    mock_coordinator.data = {}

    call = _make_call()
    await handle_refresh_packages(mock_hass, call)

    mock_client.async_refresh_package.assert_not_called()
    mock_coordinator.async_set_updated_data.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_raises_when_not_configured(mock_hass):
    mock_hass.data[DOMAIN].clear()

    call = _make_call()
    with pytest.raises(HomeAssistantError, match="not configured"):
        await handle_refresh_packages(mock_hass, call)
