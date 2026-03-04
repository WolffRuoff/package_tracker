"""Package Tracker integration for Home Assistant."""

from __future__ import annotations

import os

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api_client import ScraperApiError
from .carriers import detect_carrier
from .const import CONF_PACKAGES, CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL, DOMAIN
from .coordinator import PackageTrackerCoordinator

PLATFORMS = ["sensor"]

ADD_PACKAGE_SCHEMA = vol.Schema(
    {
        vol.Required("tracking_number"): cv.string,
        vol.Required("label"): cv.string,
        vol.Optional("carrier", default=""): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Package Tracker component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Package Tracker from a config entry."""
    scraper_url = entry.data.get(CONF_SCRAPER_URL, DEFAULT_SCRAPER_URL)
    coordinator = PackageTrackerCoordinator(hass, entry, scraper_url)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register frontend static path for the Lovelace card
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.isdir(frontend_path):
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/package_tracker", frontend_path, cache_headers=False)]
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register add_package service (once per domain)
    if not hass.services.has_service(DOMAIN, "add_package"):

        async def handle_add_package(call: ServiceCall) -> None:
            coordinators = list(hass.data[DOMAIN].values())
            if not coordinators:
                raise HomeAssistantError("Package Tracker is not configured")
            coord: PackageTrackerCoordinator = coordinators[0]
            cfg_entry = coord.entry

            tracking_number = call.data["tracking_number"].strip()
            label = call.data["label"].strip()
            carrier = call.data.get("carrier", "").strip()

            if not carrier:
                detected = detect_carrier(tracking_number)
                if detected:
                    carrier = detected.value
                else:
                    raise HomeAssistantError(
                        f"Cannot auto-detect carrier for {tracking_number}"
                    )

            packages = list(cfg_entry.options.get(CONF_PACKAGES, []))
            if any(p["tracking_number"] == tracking_number for p in packages):
                raise HomeAssistantError(
                    f"{tracking_number} is already being tracked"
                )

            client = coord._ensure_client()
            try:
                await client.async_add_package(tracking_number, carrier, label)
            except ScraperApiError as err:
                raise HomeAssistantError(f"Scraper error: {err}") from err

            packages.append(
                {"label": label, "tracking_number": tracking_number, "carrier": carrier}
            )
            hass.config_entries.async_update_entry(
                cfg_entry,
                options={**cfg_entry.options, CONF_PACKAGES: packages},
            )

        hass.services.async_register(
            DOMAIN, "add_package", handle_add_package, schema=ADD_PACKAGE_SCHEMA
        )

    # Reload on options change (package add/remove)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "add_package")
    return unload_ok
