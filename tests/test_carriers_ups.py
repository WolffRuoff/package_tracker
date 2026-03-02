"""Tests for the UPS carrier provider (validation + URL only)."""

from __future__ import annotations

import pytest

from package_tracker.carriers.ups import UPSProvider


@pytest.fixture
def provider():
    return UPSProvider()


VALID_TRACKING = "1ZABCDEF1234567890"


class TestValidateTrackingNumber:
    """Tests for UPS tracking number validation."""

    def test_valid_1z_format(self, provider):
        assert provider.validate_tracking_number("1Z12345E6605272234") is True

    def test_valid_uppercase(self, provider):
        assert provider.validate_tracking_number("1zabcdef1234567890") is True

    def test_invalid_no_1z_prefix(self, provider):
        assert provider.validate_tracking_number("2Z12345E6605272234") is False

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("1Z12345") is False

    def test_invalid_too_long(self, provider):
        assert provider.validate_tracking_number("1Z12345E66052722341X") is False


class TestTrackingUrl:
    """Tests for tracking URL generation."""

    def test_tracking_url(self, provider):
        url = provider.tracking_url(VALID_TRACKING)
        assert VALID_TRACKING in url
        assert "ups.com" in url
