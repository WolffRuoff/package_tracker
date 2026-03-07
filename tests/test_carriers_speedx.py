"""Tests for the SpeedX carrier provider (validation + URL only)."""

from __future__ import annotations

import pytest

from package_tracker.carriers.speedx import SpeedXProvider


@pytest.fixture
def provider():
    return SpeedXProvider()


class TestValidateTrackingNumber:
    def test_valid_standard(self, provider):
        assert provider.validate_tracking_number("SPXBOS039706401374") is True

    def test_valid_lowercase(self, provider):
        assert provider.validate_tracking_number("spxbos039706401374") is True

    def test_valid_strips_whitespace(self, provider):
        assert provider.validate_tracking_number("  SPXBOS039706401374  ") is True

    def test_valid_longer_hub_code(self, provider):
        assert provider.validate_tracking_number("SPXABCDE12345678") is True

    def test_invalid_missing_spx_prefix(self, provider):
        assert provider.validate_tracking_number("BOS039706401374") is False

    def test_invalid_hub_code_too_short(self, provider):
        assert provider.validate_tracking_number("SPXB039706401374") is False

    def test_invalid_hub_code_too_long(self, provider):
        assert provider.validate_tracking_number("SPXABCDEF039706401374") is False

    def test_invalid_digits_too_few(self, provider):
        assert provider.validate_tracking_number("SPXBOS1234567") is False

    def test_not_usps(self, provider):
        assert provider.validate_tracking_number("92001234567890123456") is False

    def test_not_ups(self, provider):
        assert provider.validate_tracking_number("1Z999AA10123456784") is False


class TestTrackingUrl:
    def test_contains_tracking_number(self, provider):
        url = provider.tracking_url("spxbos039706401374")
        assert "SPXBOS039706401374" in url
        assert "tracking.speedx.io" in url

    def test_uppercases_tracking_number(self, provider):
        url = provider.tracking_url("spxbos039706401374")
        assert "spxbos039706401374" not in url
