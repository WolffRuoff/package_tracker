"""Tests for scraper.util shared helpers."""

from __future__ import annotations

from datetime import timedelta

from scraper.util import parse_date, to_iso, utcnow


class TestUtcnow:
    def test_is_utc_aware(self):
        now = utcnow()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)


class TestToIso:
    def test_none_passthrough(self):
        assert to_iso(None) is None

    def test_serializes(self):
        assert to_iso(utcnow()).endswith("+00:00")


class TestParseDate:
    def test_full_date(self):
        d = parse_date("January 15, 2025")
        assert (d.year, d.month, d.day) == (2025, 1, 15)
        assert d.tzinfo is None  # carrier dates stay naive

    def test_missing_year_defaults_to_current(self):
        d = parse_date("March 7")
        assert (d.month, d.day) == (3, 7)
        assert d.year == utcnow().year

    def test_prefix_and_weekday_stripped(self):
        d = parse_date("Expected Delivery by: Friday, March 7")
        assert (d.month, d.day) == (3, 7)

    def test_day_first_with_year(self):
        d = parse_date("Saturday 7 March 2026")
        assert (d.year, d.month, d.day) == (2026, 3, 7)

    def test_monday_not_corrupted_by_on(self):
        # Regression: the "on" prefix strip must not match inside "Monday".
        d = parse_date("Monday 13 July 2026")
        assert (d.year, d.month, d.day) == (2026, 7, 13)

    def test_time_component_preserved_and_naive(self):
        d = parse_date("July 8, 2026 9:49 AM")
        assert (d.month, d.day, d.hour, d.minute) == (7, 8, 9, 49)
        assert d.tzinfo is None

    def test_invalid_returns_none(self):
        assert parse_date("not a date at all") is None

    def test_empty_returns_none(self):
        assert parse_date("") is None
