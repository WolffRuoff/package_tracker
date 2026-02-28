"""Tests for the Package Tracker config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.config_flow import (
    PackageTrackerConfigFlow,
    PackageTrackerOptionsFlow,
)
from package_tracker.const import (
    CONF_FEDEX_API_KEY,
    CONF_FEDEX_SECRET_KEY,
    CONF_PACKAGES,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_API_KEY,
    Carrier,
)


@pytest.fixture
def config_flow():
    flow = PackageTrackerConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
    )
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    return flow


def _make_options_flow(packages):
    """Create an options flow, patching HA's frame detection."""
    config_entry = MagicMock()
    config_entry.options = {CONF_PACKAGES: packages}

    with patch("homeassistant.config_entries.report_usage"):
        flow = PackageTrackerOptionsFlow(config_entry)

    flow.hass = MagicMock()
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
    )
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    flow.async_show_menu = MagicMock(
        side_effect=lambda **kwargs: {"type": "menu", **kwargs}
    )
    flow.async_abort = MagicMock(
        side_effect=lambda **kwargs: {"type": "abort", **kwargs}
    )
    return flow


@pytest.fixture
def options_flow():
    return _make_options_flow(
        [
            {
                "label": "Test Package",
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
            }
        ]
    )


class TestConfigFlowUser:
    """Tests for the initial user setup step."""

    @pytest.mark.asyncio
    async def test_shows_form_when_no_input(self, config_flow):
        result = await config_flow.async_step_user(None)
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_creates_entry_with_api_keys(self, config_flow):
        result = await config_flow.async_step_user(
            {
                CONF_USPS_API_KEY: "usps_key",
                CONF_UPS_CLIENT_ID: "ups_id",
                CONF_UPS_CLIENT_SECRET: "ups_secret",
                CONF_FEDEX_API_KEY: "fedex_key",
                CONF_FEDEX_SECRET_KEY: "fedex_secret",
            }
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_USPS_API_KEY] == "usps_key"
        assert result["data"][CONF_UPS_CLIENT_ID] == "ups_id"

    @pytest.mark.asyncio
    async def test_filters_empty_strings(self, config_flow):
        result = await config_flow.async_step_user(
            {
                CONF_USPS_API_KEY: "usps_key",
                CONF_UPS_CLIENT_ID: "",
                CONF_UPS_CLIENT_SECRET: "",
                CONF_FEDEX_API_KEY: "",
                CONF_FEDEX_SECRET_KEY: "",
            }
        )
        assert result["type"] == "create_entry"
        assert CONF_UPS_CLIENT_ID not in result["data"]
        assert CONF_USPS_API_KEY in result["data"]


class TestOptionsFlowAddPackage:
    """Tests for adding a package via options flow."""

    @pytest.mark.asyncio
    async def test_shows_menu(self, options_flow):
        result = await options_flow.async_step_init(None)
        assert result["type"] == "menu"

    @pytest.mark.asyncio
    async def test_add_package_shows_form(self, options_flow):
        result = await options_flow.async_step_add_package(None)
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_add_package_auto_detects_carrier(self, options_flow):
        result = await options_flow.async_step_add_package(
            {
                "label": "New Package",
                "tracking_number": "1Z12345E6605272234",
                "carrier": "",
            }
        )
        assert result["type"] == "create_entry"
        packages = result["data"][CONF_PACKAGES]
        added = [p for p in packages if p["tracking_number"] == "1Z12345E6605272234"]
        assert len(added) == 1
        assert added[0]["carrier"] == "ups"

    @pytest.mark.asyncio
    async def test_add_package_prevents_duplicates(self, options_flow):
        result = await options_flow.async_step_add_package(
            {
                "label": "Duplicate",
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
            }
        )
        assert result["type"] == "form"
        assert result["errors"]["tracking_number"] == "already_tracked"

    @pytest.mark.asyncio
    async def test_add_package_cannot_detect_carrier(self, options_flow):
        result = await options_flow.async_step_add_package(
            {
                "label": "Unknown",
                "tracking_number": "XYZABC",
                "carrier": "",
            }
        )
        assert result["type"] == "form"
        assert result["errors"]["carrier"] == "cannot_detect_carrier"

    @pytest.mark.asyncio
    async def test_add_package_with_explicit_carrier(self, options_flow):
        result = await options_flow.async_step_add_package(
            {
                "label": "FedEx Package",
                "tracking_number": "123456789012",
                "carrier": "fedex",
            }
        )
        assert result["type"] == "create_entry"
        packages = result["data"][CONF_PACKAGES]
        added = [p for p in packages if p["tracking_number"] == "123456789012"]
        assert added[0]["carrier"] == "fedex"


class TestOptionsFlowRemovePackage:
    """Tests for removing a package via options flow."""

    @pytest.mark.asyncio
    async def test_remove_package_shows_form(self, options_flow):
        result = await options_flow.async_step_remove_package(None)
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_remove_package(self, options_flow):
        result = await options_flow.async_step_remove_package(
            {"package": "92001234567890123456"}
        )
        assert result["type"] == "create_entry"
        packages = result["data"][CONF_PACKAGES]
        assert len(packages) == 0

    @pytest.mark.asyncio
    async def test_remove_aborts_if_no_packages(self):
        flow = _make_options_flow([])

        result = await flow.async_step_remove_package(None)
        assert result["type"] == "abort"
        assert result["reason"] == "no_packages"
