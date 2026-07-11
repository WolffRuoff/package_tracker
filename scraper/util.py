"""Shared scraper utilities."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from dateutil import parser as _dateparser

# Carrier labels that wrap a date, e.g. "Expected Delivery by:", "Delivered:".
# Stripped before parsing so dateutil sees only the date. Word boundaries keep
# "on"/"by" from matching inside words like "Monday".
_DATE_PREFIX_RE = re.compile(
    r"\b(?:expected delivery(?: by)?|estimated delivery(?: date)?"
    r"|scheduled delivery|delivered|by|on)\b\s*:?\s*",
    re.IGNORECASE,
)


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    """Serialize a datetime to an ISO-8601 string, passing through None."""
    return value.isoformat() if value is not None else None


def parse_date(text: str) -> datetime | None:
    """Parse a carrier date/time string into a naive datetime, or None.

    Handles carrier prefixes, weekday names, day/month ordering, and optional
    clock times. A missing year defaults to the current year. Returns a naive
    datetime — carrier dates are floating wall-clock values with no real
    timezone, so they must not be shifted when localized for display.
    """
    if not text:
        return None
    cleaned = _DATE_PREFIX_RE.sub("", text).strip()
    if not cleaned:
        return None
    # Naive default supplies the current year for year-less dates and keeps the
    # result naive.
    default = datetime(utcnow().year, 1, 1)
    try:
        return _dateparser.parse(cleaned, default=default)
    except (ValueError, OverflowError):
        return None
