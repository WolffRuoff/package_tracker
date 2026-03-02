"""Tests for the Package Tracker sensor platform."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.carriers.base import TrackingEvent, TrackingResult
from package_tracker.const import CONF_PACKAGES, DOMAIN, Carrier, TrackingStatus
from package_tracker.sensor import PackageTrackerSensor, async_setup_entry


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with tracking data."""
    coordinator = MagicMock()
    coordinator.data = {
        "92001234567890123456": TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="92001234567890123456",
            status=TrackingStatus.DELIVERED,
            raw_status="Delivered",
            last_updated=datetime(2025, 1, 15, 14, 30),
            estimated_delivery=datetime(2025, 1, 15),
            tracking_url="https://tools.usps.com/go/TrackConfirmAction?tLabels=92001234567890123456",
            events=[
                TrackingEvent(
                    timestamp=datetime(2025, 1, 15, 14, 30),
                    location="Springfield, IL",
                    description="Delivered",
                    status=TrackingStatus.DELIVERED,
                ),
            ],
        )
    }
    return coordinator


@pytest.fixture
def package_info():
    return {
        "label": "Test Package",
        "tracking_number": "92001234567890123456",
        "carrier": "usps",
    }


@pytest.fixture
def sensor(mock_coordinator, package_info):
    """Return a PackageTrackerSensor instance."""
    with patch.object(PackageTrackerSensor, "__init__", lambda self, *a, **kw: None):
        s = PackageTrackerSensor.__new__(PackageTrackerSensor)
        s.coordinator = mock_coordinator
        s._tracking_number = package_info["tracking_number"]
        s._label = package_info["label"]
        s._carrier = package_info["carrier"]
        s._delivered_at = package_info.get("delivered_at")
        s._attr_unique_id = f"package_tracker_{package_info['tracking_number']}"
        s._attr_name = package_info["label"]
        s._attr_icon = "mdi:package-variant"
        return s


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_creates_correct_number_of_entities(self, mock_hass):
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.options = {
            CONF_PACKAGES: [
                {"label": "Pkg1", "tracking_number": "111", "carrier": "usps"},
                {"label": "Pkg2", "tracking_number": "222", "carrier": "ups"},
            ]
        }
        mock_hass.data = {DOMAIN: {"test_entry": MagicMock()}}

        added_entities = []

        def capture_entities(entities, **kwargs):
            added_entities.extend(entities)

        def fake_init(self, coord, pkg):
            self.coordinator = coord
            self._tracking_number = pkg["tracking_number"]
            self._label = pkg["label"]
            self._carrier = pkg["carrier"]
            self._delivered_at = pkg.get("delivered_at")
            self._attr_unique_id = f"package_tracker_{pkg['tracking_number']}"
            self._attr_name = pkg["label"]
            self._attr_icon = "mdi:package-variant"

        # Patch CoordinatorEntity.__init__ to avoid HA internals
        with patch.object(PackageTrackerSensor, "__init__", fake_init):
            await async_setup_entry(mock_hass, entry, capture_entities)

        assert len(added_entities) == 2


class TestNativeValue:
    """Tests for native_value property."""

    def test_returns_status_value(self, sensor):
        assert sensor.native_value == "delivered"

    def test_returns_none_when_no_data(self, sensor):
        sensor.coordinator.data = None
        assert sensor.native_value is None

    def test_returns_none_when_tracking_not_found(self, sensor):
        sensor.coordinator.data = {}
        assert sensor.native_value is None


class TestExtraStateAttributes:
    """Tests for extra_state_attributes property."""

    def test_includes_basic_attributes(self, sensor):
        attrs = sensor.extra_state_attributes
        assert attrs["label"] == "Test Package"
        assert attrs["carrier"] == "usps"
        assert attrs["tracking_number"] == "92001234567890123456"

    def test_includes_tracking_url(self, sensor):
        attrs = sensor.extra_state_attributes
        assert attrs["tracking_url"] is not None
        assert "92001234567890123456" in attrs["tracking_url"]
        assert "usps.com" in attrs["tracking_url"]

    def test_includes_tracking_result_attributes(self, sensor):
        attrs = sensor.extra_state_attributes
        assert attrs["raw_status"] == "Delivered"
        assert attrs["last_updated"] == "2025-01-15T14:30:00"
        assert attrs["estimated_delivery"] == "2025-01-15T00:00:00"
        assert len(attrs["events"]) == 1
        assert attrs["events"][0]["description"] == "Delivered"
        assert attrs["events"][0]["location"] == "Springfield, IL"

    def test_handles_no_coordinator_data(self, sensor):
        sensor.coordinator.data = None
        attrs = sensor.extra_state_attributes
        assert attrs["label"] == "Test Package"
        assert "raw_status" not in attrs

    def test_handles_missing_result(self, sensor):
        sensor.coordinator.data = {}
        attrs = sensor.extra_state_attributes
        assert attrs["label"] == "Test Package"
        assert "raw_status" not in attrs

    def test_delivered_at_present_when_set(self, sensor):
        sensor._delivered_at = "2025-01-15T14:30:00+00:00"
        attrs = sensor.extra_state_attributes
        assert attrs["delivered_at"] == "2025-01-15T14:30:00+00:00"

    def test_delivered_at_absent_when_not_set(self, sensor):
        sensor._delivered_at = None
        attrs = sensor.extra_state_attributes
        assert "delivered_at" not in attrs
