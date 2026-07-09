"""SQLite-backed storage for tracked packages and results."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import aiosqlite

from .carriers.base import TrackingResult
from .const import Carrier, TrackingStatus
from .util import to_iso

_LOGGER = logging.getLogger(__name__)


class PackageStore:
    """Async SQLite storage for packages and tracking results."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """Initialize the database connection and create tables."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS packages (
                tracking_number TEXT PRIMARY KEY,
                carrier TEXT NOT NULL,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS tracking_results (
                tracking_number TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                raw_status TEXT,
                estimated_delivery TEXT,
                last_updated TEXT,
                events_json TEXT,
                FOREIGN KEY (tracking_number) REFERENCES packages(tracking_number)
                    ON DELETE CASCADE
            )
            """
        )
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def get_all_packages(
        self,
    ) -> list[dict]:
        """Return all packages with their latest tracking results."""
        assert self._db is not None
        cursor = await self._db.execute(
            """
            SELECT p.tracking_number, p.carrier, p.label, p.created_at,
                   COALESCE(r.status, ?) AS status,
                   COALESCE(r.raw_status, '') AS raw_status,
                   r.estimated_delivery,
                   r.last_updated,
                   r.events_json
            FROM packages p
            LEFT JOIN tracking_results r ON p.tracking_number = r.tracking_number
            ORDER BY p.created_at DESC
            """,
            (TrackingStatus.UNKNOWN,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def add_package(
        self, tracking_number: str, carrier: str, label: str
    ) -> dict | None:
        """Add a package to track. Returns the package dict or None if duplicate."""
        assert self._db is not None
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._db.execute(
                "INSERT INTO packages (tracking_number, carrier, label, created_at) "
                "VALUES (?, ?, ?, ?)",
                (tracking_number, carrier, label, now),
            )
            await self._db.commit()
            return {
                "tracking_number": tracking_number,
                "carrier": carrier,
                "label": label,
                "created_at": now,
            }
        except aiosqlite.IntegrityError:
            return None

    async def remove_package(self, tracking_number: str) -> bool:
        """Remove a package. Returns True if deleted, False if not found."""
        assert self._db is not None
        cursor = await self._db.execute(
            "DELETE FROM packages WHERE tracking_number = ?", (tracking_number,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_package(self, tracking_number: str) -> dict | None:
        """Return a single package with its latest tracking result."""
        assert self._db is not None
        cursor = await self._db.execute(
            """
            SELECT p.tracking_number, p.carrier, p.label, p.created_at,
                   COALESCE(r.status, ?) AS status,
                   COALESCE(r.raw_status, '') AS raw_status,
                   r.estimated_delivery, r.last_updated, r.events_json
            FROM packages p
            LEFT JOIN tracking_results r ON p.tracking_number = r.tracking_number
            WHERE p.tracking_number = ?
            """,
            (TrackingStatus.UNKNOWN, tracking_number),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_tracking_result(self, tracking_number: str) -> dict | None:
        """Return the latest tracking result for a package."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM tracking_results WHERE tracking_number = ?",
            (tracking_number,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def save_result(self, result: TrackingResult) -> None:
        """Serialize and persist a TrackingResult (domain-level upsert)."""
        events_json = json.dumps(
            [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "location": e.location,
                    "description": e.description,
                    "status": e.status.value,
                }
                for e in result.events
            ]
        )
        await self.save_tracking_result(
            tracking_number=result.tracking_number,
            status=result.status.value,
            raw_status=result.raw_status,
            estimated_delivery=to_iso(result.estimated_delivery),
            last_updated=to_iso(result.last_updated),
            events_json=events_json,
        )

    async def save_tracking_result(
        self,
        tracking_number: str,
        status: str,
        raw_status: str,
        estimated_delivery: str | None,
        last_updated: str | None,
        events_json: str,
    ) -> None:
        """Save or update a tracking result (low-level column write)."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO tracking_results
                (tracking_number, status, raw_status, estimated_delivery,
                 last_updated, events_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tracking_number) DO UPDATE SET
                status = excluded.status,
                raw_status = excluded.raw_status,
                estimated_delivery = excluded.estimated_delivery,
                last_updated = excluded.last_updated,
                events_json = excluded.events_json
            """,
            (
                tracking_number,
                status,
                raw_status,
                estimated_delivery,
                last_updated,
                events_json,
            ),
        )
        await self._db.commit()
