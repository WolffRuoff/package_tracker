"""Tests for the PackageTrackerCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.carriers.base import TrackingResult
from package_tracker.const import (
    CONF_FEDEX_API_KEY,
    CONF_FEDEX_SECRET_KEY,
    CONF_PACKAGES,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_API_KEY,
    Carrier,
    TrackingStatus,
)
from package_tracker.coordinator import PackageTrackerCoordinator


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Create a coordinator with mocked providers."""
    with patch(
        "package_tracker.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
        coord.hass = mock_hass
        coord.entry = mock_config_entry
        coord._providers = {}
        coord.data = None
        coord.logger = MagicMock()
        coord.name = "package_tracker"
        coord._init_providers()
        return coord


class TestInitProviders:
    """Tests for _init_providers."""

    def test_all_providers_created(self, coordinator):
        assert Carrier.USPS in coordinator._providers
        assert Carrier.UPS in coordinator._providers
        assert Carrier.FEDEX in coordinator._providers

    def test_skips_missing_usps_key(self, mock_hass):
        entry = MagicMock()
        entry.data = {
            CONF_UPS_CLIENT_ID: "id",
            CONF_UPS_CLIENT_SECRET: "secret",
        }
        entry.options = {CONF_PACKAGES: []}

        with patch(
            "package_tracker.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
            coord.hass = mock_hass
            coord.entry = entry
            coord._providers = {}
            coord.data = None
            coord.logger = MagicMock()
            coord.name = "package_tracker"
            coord._init_providers()

        assert Carrier.USPS not in coord._providers
        assert Carrier.UPS in coord._providers

    def test_skips_partial_ups_keys(self, mock_hass):
        entry = MagicMock()
        entry.data = {CONF_UPS_CLIENT_ID: "id"}  # missing secret
        entry.options = {CONF_PACKAGES: []}

        with patch(
            "package_tracker.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
            coord.hass = mock_hass
            coord.entry = entry
            coord._providers = {}
            coord.data = None
            coord.logger = MagicMock()
            coord.name = "package_tracker"
            coord._init_providers()

        assert Carrier.UPS not in coord._providers


class TestGetPackages:
    """Tests for get_packages."""

    def test_returns_packages(self, coordinator):
        packages = coordinator.get_packages()
        assert len(packages) == 1
        assert packages[0]["tracking_number"] == "92001234567890123456"

    def test_returns_empty_when_no_packages(self, mock_hass):
        entry = MagicMock()
        entry.data = {}
        entry.options = {}

        with patch(
            "package_tracker.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
            coord.hass = mock_hass
            coord.entry = entry
            coord._providers = {}
            coord.data = None
            coord.logger = MagicMock()
            coord.name = "package_tracker"

        assert coord.get_packages() == []


class TestAsyncUpdateData:
    """Tests for _async_update_data."""

    @pytest.mark.asyncio
    async def test_calls_provider_and_returns_results(self, coordinator):
        mock_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="92001234567890123456",
            status=TrackingStatus.DELIVERED,
        )
        mock_provider = AsyncMock()
        mock_provider.async_track.return_value = mock_result
        coordinator._providers[Carrier.USPS] = mock_provider

        results = await coordinator._async_update_data()

        assert "92001234567890123456" in results
        assert results["92001234567890123456"].status == TrackingStatus.DELIVERED
        mock_provider.async_track.assert_called_once_with("92001234567890123456")

    @pytest.mark.asyncio
    async def test_retains_previous_data_on_failure(self, coordinator):
        previous_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="92001234567890123456",
            status=TrackingStatus.IN_TRANSIT,
        )
        coordinator.data = {"92001234567890123456": previous_result}

        mock_provider = AsyncMock()
        mock_provider.async_track.side_effect = Exception("API error")
        coordinator._providers[Carrier.USPS] = mock_provider

        results = await coordinator._async_update_data()

        assert "92001234567890123456" in results
        assert results["92001234567890123456"].status == TrackingStatus.IN_TRANSIT

    @pytest.mark.asyncio
    async def test_skips_missing_provider(self, coordinator):
        coordinator._providers = {}  # No providers
        coordinator.data = None

        results = await coordinator._async_update_data()

        assert "92001234567890123456" not in results
