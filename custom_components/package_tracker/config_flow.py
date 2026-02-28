"""Config flow for Package Tracker integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .carriers import detect_carrier
from .const import (
    CONF_FEDEX_API_KEY,
    CONF_FEDEX_SECRET_KEY,
    CONF_PACKAGES,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_API_KEY,
    DOMAIN,
    Carrier,
)


class PackageTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for Package Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step — collect API keys."""
        if user_input is not None:
            # Filter out empty strings
            data = {k: v for k, v in user_input.items() if v}
            return self.async_create_entry(
                title="Package Tracker",
                data=data,
                options={CONF_PACKAGES: []},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USPS_API_KEY, default=""): str,
                    vol.Optional(CONF_UPS_CLIENT_ID, default=""): str,
                    vol.Optional(CONF_UPS_CLIENT_SECRET, default=""): str,
                    vol.Optional(CONF_FEDEX_API_KEY, default=""): str,
                    vol.Optional(CONF_FEDEX_SECRET_KEY, default=""): str,
                }
            ),
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
            menu_options=["add_package", "remove_package"],
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
