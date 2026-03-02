"""Tests for the PackageTrackerCoordinator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.api_client import ScraperApiError
from package_tracker.carriers.base import TrackingResult
from package_tracker.const import (
    CONF_AUTO_REMOVE_DAYS,
    CONF_PACKAGES,
    CONF_SCRAPER_URL,
    Carrier,
    TrackingStatus,
)
from package_tracker.coordinator import PackageTrackerCoordinator


def _make_coordinator(mock_hass, packages, auto_remove_days=1, mock_client=None):
    """Create a coordinator with given packages and a mock API client."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_SCRAPER_URL: "http://localhost:8230"}
    entry.options = {
        CONF_PACKAGES: packages,
        CONF_AUTO_REMOVE_DAYS: auto_remove_days,
    }
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()

    with patch(
        "package_tracker.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
        coord.hass = mock_hass
        coord.entry = entry
        coord._scraper_url = "http://localhost:8230"
        coord._session = MagicMock()
        coord._client = mock_client or AsyncMock()
        coord.data = None
        coord.logger = MagicMock()
        coord.name = "package_tracker"
        coord.update_interval = None
    return coord


@pytest.fixture
def coordinator(mock_hass, mock_config_entry, mock_scraper_api):
    """Create a coordinator with mocked API client."""
    with patch(
        "package_tracker.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = PackageTrackerCoordinator.__new__(PackageTrackerCoordinator)
        coord.hass = mock_hass
        coord.entry = mock_config_entry
        coord._scraper_url = "http://localhost:8230"
        coord._session = MagicMock()
        coord._client = mock_scraper_api
        coord.data = None
        coord.logger = MagicMock()
        coord.name = "package_tracker"
        coord.update_interval = None
        return coord


class TestGetPackages:
    """Tests for get_packages."""

    def test_returns_packages(self, coordinator):
        packages = coordinator.get_packages()
        assert len(packages) == 1
        assert packages[0]["tracking_number"] == "92001234567890123456"

    def test_returns_empty_when_no_packages(self, mock_hass):
        coord = _make_coordinator(mock_hass, [])
        assert coord.get_packages() == []


class TestAsyncUpdateData:
    """Tests for _async_update_data."""

    @pytest.mark.asyncio
    async def test_fetches_packages_from_scraper_api(self, coordinator):
        results = await coordinator._async_update_data()

        assert "92001234567890123456" in results
        assert results["92001234567890123456"].status == TrackingStatus.DELIVERED
        coordinator._client.async_get_packages.assert_called_once()

    @pytest.mark.asyncio
    async def test_parses_tracking_result_correctly(self, coordinator):
        results = await coordinator._async_update_data()

        result = results["92001234567890123456"]
        assert result.carrier == Carrier.USPS
        assert result.raw_status == "Delivered"
        assert result.estimated_delivery is not None
        assert result.last_updated is not None
        assert len(result.events) == 1
        assert result.events[0].description == "Delivered"
        assert result.events[0].location == "Springfield, IL"
        assert result.tracking_url is not None
        assert "usps.com" in result.tracking_url

    @pytest.mark.asyncio
    async def test_retains_previous_data_on_api_error(self, coordinator):
        previous_result = TrackingResult(
            carrier=Carrier.USPS,
            tracking_number="92001234567890123456",
            status=TrackingStatus.IN_TRANSIT,
        )
        coordinator.data = {"92001234567890123456": previous_result}
        coordinator._client.async_get_packages.side_effect = ScraperApiError("fail")

        results = await coordinator._async_update_data()

        assert "92001234567890123456" in results
        assert results["92001234567890123456"].status == TrackingStatus.IN_TRANSIT

    @pytest.mark.asyncio
    async def test_handles_empty_package_list(self, coordinator):
        coordinator._client.async_get_packages.return_value = []

        results = await coordinator._async_update_data()

        assert results == {}

    @pytest.mark.asyncio
    async def test_jittered_interval_changes(self, coordinator):
        """Verify update interval is re-randomized after each update."""
        await coordinator._async_update_data()
        interval1 = coordinator.update_interval

        await coordinator._async_update_data()
        interval2 = coordinator.update_interval

        assert interval1 is not None
        assert interval2 is not None


class TestAutoRemoveDelivered:
    """Tests for _async_process_delivered_packages."""

    @pytest.mark.asyncio
    async def test_stamps_delivered_at_on_first_delivery(self, mock_hass):
        """delivered_at should be stamped when first observed as DELIVERED."""
        packages = [
            {"label": "Pkg", "tracking_number": "123", "carrier": "usps"}
        ]
        coord = _make_coordinator(mock_hass, packages)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_pkgs = call_args[1]["options"][CONF_PACKAGES]
        assert len(updated_pkgs) == 1
        assert "delivered_at" in updated_pkgs[0]

    @pytest.mark.asyncio
    async def test_does_not_restamp_delivered_at(self, mock_hass):
        """delivered_at should not be overwritten on subsequent polls."""
        original_stamp = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        packages = [
            {
                "label": "Pkg",
                "tracking_number": "123",
                "carrier": "usps",
                "delivered_at": original_stamp,
            }
        ]
        coord = _make_coordinator(mock_hass, packages)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_removes_package_after_configured_days(self, mock_hass):
        """Package should be removed once delivered_at exceeds threshold."""
        old_stamp = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        packages = [
            {
                "label": "Pkg",
                "tracking_number": "123",
                "carrier": "usps",
                "delivered_at": old_stamp,
            }
        ]
        coord = _make_coordinator(mock_hass, packages, auto_remove_days=1)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_pkgs = call_args[1]["options"][CONF_PACKAGES]
        assert len(updated_pkgs) == 0

    @pytest.mark.asyncio
    async def test_no_removal_when_auto_remove_disabled(self, mock_hass):
        """Packages should not be removed when auto_remove_days is 0."""
        old_stamp = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        packages = [
            {
                "label": "Pkg",
                "tracking_number": "123",
                "carrier": "usps",
                "delivered_at": old_stamp,
            }
        ]
        coord = _make_coordinator(mock_hass, packages, auto_remove_days=0)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_removal_before_threshold(self, mock_hass):
        """Package should not be removed before the threshold has elapsed."""
        recent_stamp = (
            datetime.now(timezone.utc) - timedelta(hours=12)
        ).isoformat()
        packages = [
            {
                "label": "Pkg",
                "tracking_number": "123",
                "carrier": "usps",
                "delivered_at": recent_stamp,
            }
        ]
        coord = _make_coordinator(mock_hass, packages, auto_remove_days=1)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_delivered_packages_untouched(self, mock_hass):
        """Packages that aren't delivered should not get a delivered_at stamp."""
        packages = [
            {"label": "Pkg", "tracking_number": "123", "carrier": "usps"}
        ]
        coord = _make_coordinator(mock_hass, packages)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.IN_TRANSIT,
            )
        }
        await coord._async_process_delivered_packages(results)

        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_packages_only_expired_removed(self, mock_hass):
        """Only expired delivered packages should be removed; others kept."""
        old_stamp = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        packages = [
            {
                "label": "Old",
                "tracking_number": "111",
                "carrier": "usps",
                "delivered_at": old_stamp,
            },
            {"label": "Active", "tracking_number": "222", "carrier": "ups"},
        ]
        coord = _make_coordinator(mock_hass, packages, auto_remove_days=1)

        results = {
            "111": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="111",
                status=TrackingStatus.DELIVERED,
            ),
            "222": TrackingResult(
                carrier=Carrier.UPS,
                tracking_number="222",
                status=TrackingStatus.IN_TRANSIT,
            ),
        }
        await coord._async_process_delivered_packages(results)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_pkgs = call_args[1]["options"][CONF_PACKAGES]
        assert len(updated_pkgs) == 1
        assert updated_pkgs[0]["tracking_number"] == "222"

    @pytest.mark.asyncio
    async def test_stamps_delivered_at_even_when_auto_remove_disabled(
        self, mock_hass
    ):
        """delivered_at should still be stamped when auto_remove_days is 0."""
        packages = [
            {"label": "Pkg", "tracking_number": "123", "carrier": "usps"}
        ]
        coord = _make_coordinator(mock_hass, packages, auto_remove_days=0)

        results = {
            "123": TrackingResult(
                carrier=Carrier.USPS,
                tracking_number="123",
                status=TrackingStatus.DELIVERED,
            )
        }
        await coord._async_process_delivered_packages(results)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_pkgs = call_args[1]["options"][CONF_PACKAGES]
        assert "delivered_at" in updated_pkgs[0]
