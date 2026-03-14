"""Service handlers for Package Tracker."""

from __future__ import annotations

import logging
from functools import partial

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api_client import ScraperApiError
from .carriers import detect_carrier
from .const import CONF_PACKAGES, DOMAIN
from .coordinator import PackageTrackerCoordinator, parse_package_dict

_LOGGER = logging.getLogger(__name__)

ADD_PACKAGE_SCHEMA = vol.Schema(
    {
        vol.Required("tracking_number"): cv.string,
        vol.Required("label"): cv.string,
        vol.Optional("carrier", default=""): cv.string,
    }
)


def _get_coordinator(hass: HomeAssistant) -> PackageTrackerCoordinator:
    """Get the first coordinator from hass.data or raise."""
    coordinators = list(hass.data[DOMAIN].values())
    if not coordinators:
        raise HomeAssistantError("Package Tracker is not configured")
    return coordinators[0]


async def handle_add_package(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the add_package service call."""
    coord = _get_coordinator(hass)
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

    try:
        pkg_data = await client.async_refresh_package(tracking_number)
        result = parse_package_dict(pkg_data)
        if result:
            new_data = {**(coord.data or {}), tracking_number: result}
            coord.async_set_updated_data(new_data)
    except ScraperApiError:
        _LOGGER.warning(
            "Could not trigger immediate refresh for %s; will scrape on next cycle",
            tracking_number,
        )

    packages.append(
        {"label": label, "tracking_number": tracking_number, "carrier": carrier}
    )
    hass.config_entries.async_update_entry(
        cfg_entry,
        options={**cfg_entry.options, CONF_PACKAGES: packages},
    )


async def handle_get_carriers(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Return the list of carriers supported by the scraper."""
    coord = _get_coordinator(hass)
    return {"carriers": coord.supported_carriers}


async def handle_refresh_packages(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the refresh_packages service call."""
    coord = _get_coordinator(hass)

    client = coord._ensure_client()
    current_data = dict(coord.data or {})
    tracking_numbers = list(current_data.keys())

    if not tracking_numbers:
        return

    for tn in tracking_numbers:
        try:
            pkg_data = await client.async_refresh_package(tn)
            result = parse_package_dict(pkg_data)
            if result:
                current_data[tn] = result
        except ScraperApiError:
            _LOGGER.warning(
                "Failed to refresh %s; keeping cached data", tn
            )

    coord.async_set_updated_data(current_data)


def register_services(hass: HomeAssistant) -> None:
    """Register package tracker services (once per domain)."""
    if not hass.services.has_service(DOMAIN, "add_package"):
        hass.services.async_register(
            DOMAIN,
            "add_package",
            partial(handle_add_package, hass),
            schema=ADD_PACKAGE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, "refresh_packages"):
        hass.services.async_register(
            DOMAIN,
            "refresh_packages",
            partial(handle_refresh_packages, hass),
        )

    if not hass.services.has_service(DOMAIN, "get_carriers"):
        hass.services.async_register(
            DOMAIN,
            "get_carriers",
            partial(handle_get_carriers, hass),
            supports_response=SupportsResponse.ONLY,
        )


def unregister_services(hass: HomeAssistant) -> None:
    """Remove package tracker services."""
    hass.services.async_remove(DOMAIN, "add_package")
    hass.services.async_remove(DOMAIN, "refresh_packages")
    hass.services.async_remove(DOMAIN, "get_carriers")
