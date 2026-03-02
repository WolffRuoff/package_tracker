"""Tests for the FedEx carrier provider (validation + URL only)."""

from __future__ import annotations

import pytest

from package_tracker.carriers.fedex import FedExProvider


@pytest.fixture
def provider():
    return FedExProvider()


VALID_TRACKING_12 = "123456789012"
VALID_TRACKING_15 = "123456789012345"


class TestValidateTrackingNumber:
    """Tests for FedEx tracking number validation."""

    def test_valid_12_digit(self, provider):
        assert provider.validate_tracking_number("123456789012") is True

    def test_valid_15_digit(self, provider):
        assert provider.validate_tracking_number("123456789012345") is True

    def test_valid_96_prefix(self, provider):
        assert provider.validate_tracking_number("96123456789012345678") is True

    def test_valid_dt_prefix(self, provider):
        assert provider.validate_tracking_number("DT123456789012") is True

    def test_valid_dt_case_insensitive(self, provider):
        assert provider.validate_tracking_number("dt123456789012") is True

    def test_invalid_too_short(self, provider):
        assert provider.validate_tracking_number("12345") is False

    def test_invalid_letters(self, provider):
        assert provider.validate_tracking_number("12345ABCDE12") is False

    def test_invalid_1z_prefix(self, provider):
        """Should not match UPS-style tracking numbers."""
        assert provider.validate_tracking_number("1Z12345E6605272234") is False


class TestTrackingUrl:
    """Tests for tracking URL generation."""

    def test_tracking_url(self, provider):
        url = provider.tracking_url(VALID_TRACKING_12)
        assert VALID_TRACKING_12 in url
        assert "fedex.com" in url
