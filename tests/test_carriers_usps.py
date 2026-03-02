"""Tests for the USPS carrier provider (validation + URL only)."""

from __future__ import annotations

import pytest

from package_tracker.carriers.usps import USPSProvider


@pytest.fixture
def provider():
    return USPSProvider()


class TestValidateTrackingNumber:
    """Tests for USPS tracking number validation."""

    def test_valid_20_digit(self, provider):
        assert provider.validate_tracking_number("92001234567890123456") is True

    def test_valid_22_digit(self, provider):
        assert provider.validate_tracking_number("9200123456789012345678") is True

    def test_valid_service_prefix(self, provider):
        assert provider.validate_tracking_number("EA123456789US") is True

    def test_valid_service_prefix_ec(self, provider):
        assert provider.validate_tracking_number("EC123456789US") is True

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_invalid_letters_in_numeric(self, provider):
        assert provider.validate_tracking_number("9200ABCD567890123456") is False

    def test_invalid_service_prefix_wrong_country(self, provider):
        assert provider.validate_tracking_number("EA123456789UK") is False

    def test_strips_whitespace(self, provider):
        assert provider.validate_tracking_number("  EA123456789US  ") is True


class TestTrackingUrl:
    """Tests for tracking URL generation."""

    def test_tracking_url(self, provider):
        url = provider.tracking_url("92001234567890123456")
        assert "92001234567890123456" in url
        assert "tools.usps.com" in url
