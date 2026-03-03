"""Config flow for Package Tracker integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api_client import ScraperApiClient, ScraperApiError
from .carriers import detect_carrier
from .const import (
    CONF_AUTO_REMOVE_DAYS,
    CONF_PACKAGES,
    CONF_SCRAPER_URL,
    DEFAULT_AUTO_REMOVE_DAYS,
    DEFAULT_SCRAPER_URL,
    DOMAIN,
    Carrier,
)


class PackageTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for Package Tracker."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step — collect scraper URL and validate connection."""
        errors: dict[str, str] = {}
        suggested_url = DEFAULT_SCRAPER_URL

        if user_input is not None:
            scraper_url = user_input[CONF_SCRAPER_URL].rstrip("/")
            suggested_url = scraper_url

            # Validate connection to scraper
            try:
                async with aiohttp.ClientSession() as session:
                    client = ScraperApiClient(scraper_url, session)
                    await client.async_health()
            except (ScraperApiError, aiohttp.ClientError):
                errors[CONF_SCRAPER_URL] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title="Package Tracker",
                    data={CONF_SCRAPER_URL: scraper_url},
                    options={CONF_PACKAGES: []},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCRAPER_URL, default=suggested_url): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> PackageTrackerOptionsFlow:
        """Get the options flow handler."""
        return PackageTrackerOptionsFlow(config_entry)


class PackageTrackerOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle options flow for Package Tracker (add/remove packages)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the menu: add or remove packages."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_package", "remove_package", "settings"],
        )

    async def async_step_add_package(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new package to track."""
        errors: dict[str, str] = {}

        if user_input is not None:
            tracking_number = user_input["tracking_number"].strip()
            carrier = user_input.get("carrier", "")
            label = user_input["label"].strip()

            # Auto-detect carrier if not specified
            if not carrier:
                detected = detect_carrier(tracking_number)
                if detected:
                    carrier = detected.value
                else:
                    errors["carrier"] = "cannot_detect_carrier"

            if not errors:
                packages = list(self.options.get(CONF_PACKAGES, []))
                # Check for duplicates
                for pkg in packages:
                    if pkg["tracking_number"] == tracking_number:
                        errors["tracking_number"] = "already_tracked"
                        break

            if not errors:
                # Forward add to scraper API
                scraper_url = self.config_entry.data.get(
                    CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL
                )
                try:
                    async with aiohttp.ClientSession() as session:
                        client = ScraperApiClient(scraper_url, session)
                        await client.async_add_package(
                            tracking_number, carrier, label
                        )
                except (ScraperApiError, aiohttp.ClientError):
                    errors["base"] = "scraper_error"

            if not errors:
                packages.append(
                    {
                        "label": label,
                        "tracking_number": tracking_number,
                        "carrier": carrier,
                    }
                )
                return self.async_create_entry(
                    data={**self.options, CONF_PACKAGES: packages}
                )

        carrier_options = {c.value: c.value.upper() for c in Carrier}

        return self.async_show_form(
            step_id="add_package",
            data_schema=vol.Schema(
                {
                    vol.Required("label"): str,
                    vol.Required("tracking_number"): str,
                    vol.Optional("carrier", default=""): vol.In(
                        {"": "Auto-detect", **carrier_options}
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_package(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a tracked package."""
        packages = list(self.options.get(CONF_PACKAGES, []))

        if user_input is not None:
            tracking_to_remove = user_input["package"]

            # Forward remove to scraper API
            scraper_url = self.config_entry.data.get(
                CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL
            )
            try:
                async with aiohttp.ClientSession() as session:
                    client = ScraperApiClient(scraper_url, session)
                    await client.async_remove_package(tracking_to_remove)
            except (ScraperApiError, aiohttp.ClientError):
                pass  # Best-effort; still remove locally

            packages = [
                p for p in packages if p["tracking_number"] != tracking_to_remove
            ]
            return self.async_create_entry(
                data={**self.options, CONF_PACKAGES: packages}
            )

        if not packages:
            return self.async_abort(reason="no_packages")

        package_options = {
            p["tracking_number"]: f"{p['label']} ({p['tracking_number']})"
            for p in packages
        }

        return self.async_show_form(
            step_id="remove_package",
            data_schema=vol.Schema(
                {
                    vol.Required("package"): vol.In(package_options),
                }
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure integration settings."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.options,
                    CONF_AUTO_REMOVE_DAYS: user_input[CONF_AUTO_REMOVE_DAYS],
                }
            )

        current = self.options.get(CONF_AUTO_REMOVE_DAYS, DEFAULT_AUTO_REMOVE_DAYS)

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTO_REMOVE_DAYS, default=current
                    ): vol.All(int, vol.Range(min=0)),
                }
            ),
        )
