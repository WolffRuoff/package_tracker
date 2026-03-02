"""Tests for the Package Tracker config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.config_flow import (
    PackageTrackerConfigFlow,
    PackageTrackerOptionsFlow,
)
from package_tracker.const import (
    CONF_AUTO_REMOVE_DAYS,
    CONF_PACKAGES,
    CONF_SCRAPER_URL,
    DEFAULT_SCRAPER_URL,
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


def _make_options_flow(packages, scraper_url=DEFAULT_SCRAPER_URL):
    """Create an options flow, patching HA's frame detection."""
    config_entry = MagicMock()
    config_entry.options = {CONF_PACKAGES: packages}
    config_entry.data = {CONF_SCRAPER_URL: scraper_url}

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
def options_flow(mock_scraper_api):
    flow = _make_options_flow(
        [
            {
                "label": "Test Package",
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
            }
        ]
    )
    return flow


class TestConfigFlowUser:
    """Tests for the initial user setup step."""

    @pytest.mark.asyncio
    async def test_shows_form_when_no_input(self, config_flow):
        result = await config_flow.async_step_user(None)
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_creates_entry_with_valid_scraper_url(self, config_flow):
        """Successful connection creates entry with scraper URL in data."""
        with patch(
            "package_tracker.config_flow.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            # Mock the health check to succeed
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(
                return_value={"status": "ok", "version": "2.0.0"}
            )
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_session.get = MagicMock(return_value=mock_resp)

            result = await config_flow.async_step_user(
                {CONF_SCRAPER_URL: "http://localhost:8230"}
            )

        assert result["type"] == "create_entry"
        assert result["data"][CONF_SCRAPER_URL] == "http://localhost:8230"
        assert result["options"] == {CONF_PACKAGES: []}

    @pytest.mark.asyncio
    async def test_shows_error_on_connection_failure(self, config_flow):
        """Failed connection shows error."""
        with patch(
            "package_tracker.config_flow.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            import aiohttp

            mock_session.get = MagicMock(
                side_effect=aiohttp.ClientError("Connection refused")
            )

            result = await config_flow.async_step_user(
                {CONF_SCRAPER_URL: "http://bad-host:9999"}
            )

        assert result["type"] == "form"
        assert result["errors"][CONF_SCRAPER_URL] == "cannot_connect"


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
        with patch(
            "package_tracker.config_flow.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_resp = AsyncMock()
            mock_resp.status = 201
            mock_resp.content_length = 100
            mock_resp.json = AsyncMock(return_value={})
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_session.post = MagicMock(return_value=mock_resp)

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
        with patch(
            "package_tracker.config_flow.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_resp = AsyncMock()
            mock_resp.status = 201
            mock_resp.content_length = 100
            mock_resp.json = AsyncMock(return_value={})
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_session.post = MagicMock(return_value=mock_resp)

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
        with patch(
            "package_tracker.config_flow.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_resp = AsyncMock()
            mock_resp.status = 204
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_session.delete = MagicMock(return_value=mock_resp)

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


class TestOptionsFlowSettings:
    """Tests for the settings step in options flow."""

    @pytest.mark.asyncio
    async def test_menu_includes_settings(self, options_flow):
        result = await options_flow.async_step_init(None)
        assert result["type"] == "menu"
        assert "settings" in result["menu_options"]

    @pytest.mark.asyncio
    async def test_settings_shows_form_with_default(self, options_flow):
        result = await options_flow.async_step_settings(None)
        assert result["type"] == "form"
        assert result["step_id"] == "settings"

    @pytest.mark.asyncio
    async def test_settings_saves_value_and_preserves_packages(self, options_flow):
        result = await options_flow.async_step_settings(
            {CONF_AUTO_REMOVE_DAYS: 3}
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_AUTO_REMOVE_DAYS] == 3
        assert len(result["data"][CONF_PACKAGES]) == 1
