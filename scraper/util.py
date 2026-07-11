"""Shared scraper utilities."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    """Serialize a datetime to an ISO-8601 string, passing through None."""
    return value.isoformat() if value is not None else None
