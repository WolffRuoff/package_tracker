"""Sensor platform for Package Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PACKAGES, DOMAIN
from .coordinator import PackageTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Package Tracker sensors from a config entry."""
    coordinator: PackageTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]

    packages = entry.options.get(CONF_PACKAGES, [])
    entities = [
        PackageTrackerSensor(coordinator, pkg)
        for pkg in packages
    ]

    async_add_entities(entities, update_before_add=False)


class PackageTrackerSensor(CoordinatorEntity[PackageTrackerCoordinator], SensorEntity):
    """Sensor representing a tracked package."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        package_info: dict[str, str],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._tracking_number = package_info["tracking_number"]
        self._label = package_info["label"]
        self._carrier = package_info["carrier"]

        self._attr_unique_id = f"package_tracker_{self._tracking_number}"
        self._attr_name = self._label
        self._attr_icon = "mdi:package-variant"

    @property
    def native_value(self) -> str | None:
        """Return the tracking status as the sensor state."""
        if self.coordinator.data and self._tracking_number in self.coordinator.data:
            return self.coordinator.data[self._tracking_number].status.value
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for the sensor."""
        attrs: dict[str, Any] = {
            "label": self._label,
            "carrier": self._carrier,
            "tracking_number": self._tracking_number,
        }

        if not self.coordinator.data:
            return attrs

        result = self.coordinator.data.get(self._tracking_number)
        if not result:
            return attrs

        attrs["raw_status"] = result.raw_status
        attrs["last_updated"] = (
            result.last_updated.isoformat() if result.last_updated else None
        )
        attrs["estimated_delivery"] = (
            result.estimated_delivery.isoformat()
            if result.estimated_delivery
            else None
        )
        attrs["events"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "location": e.location,
                "description": e.description,
                "status": e.status.value,
            }
            for e in result.events
        ]

        return attrs
