"""FastAPI application for the package tracker scraper."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager

from camoufox.async_api import AsyncCamoufox
from fastapi import FastAPI, HTTPException

from .carriers import get_provider
from .const import DB_PATH, DEFAULT_PORT, Carrier
from .models import (
    AddPackageRequest,
    HealthResponse,
    PackageResponse,
    TrackingEventResponse,
)
from .scheduler import Scheduler
from .storage import PackageStore

_LOGGER = logging.getLogger(__name__)

from importlib.metadata import version as _pkg_version

VERSION = _pkg_version("package-tracker-scraper")

store = PackageStore(os.environ.get("DB_PATH", DB_PATH))
scheduler: Scheduler | None = None
_camoufox: AsyncCamoufox | None = None
_browser = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start browser and scheduler on startup, clean up on shutdown."""
    global scheduler, _camoufox, _browser

    await store.init_db()

    _camoufox = AsyncCamoufox(headless=True, humanize=True, geoip=True, enable_cache=True)
    _browser = await _camoufox.__aenter__()
    _LOGGER.info("Camoufox browser launched")

    scheduler = Scheduler(store, _browser)
    scheduler.start()
    _LOGGER.info("Scheduler started")

    yield

    if scheduler:
        await scheduler.stop()
    if _camoufox:
        await _camoufox.__aexit__(None, None, None)
    await store.close()
    _LOGGER.info("Shutdown complete")


app = FastAPI(title="Package Tracker Scraper", version=VERSION, lifespan=lifespan)


def _build_package_response(pkg: dict) -> PackageResponse:
    """Convert a storage row dict into a PackageResponse."""
    carrier = Carrier(pkg["carrier"])
    provider = get_provider(carrier)
    tracking_url = provider.tracking_url(pkg["tracking_number"])

    events_raw = pkg.get("events_json")
    events = []
    if events_raw:
        for e in json.loads(events_raw):
            events.append(
                TrackingEventResponse(
                    timestamp=e["timestamp"],
                    location=e["location"],
                    description=e["description"],
                    status=e["status"],
                )
            )

    return PackageResponse(
        tracking_number=pkg["tracking_number"],
        carrier=carrier,
        label=pkg["label"],
        created_at=pkg["created_at"],
        status=pkg.get("status", "unknown"),
        raw_status=pkg.get("raw_status", ""),
        estimated_delivery=pkg.get("estimated_delivery"),
        last_updated=pkg.get("last_updated"),
        tracking_url=tracking_url,
        events=events,
    )


@app.get("/api/packages", response_model=list[PackageResponse])
async def get_packages():
    """Return all packages with latest tracking results."""
    packages = await store.get_all_packages()
    return [_build_package_response(pkg) for pkg in packages]


@app.post("/api/packages", response_model=PackageResponse, status_code=201)
async def add_package(request: AddPackageRequest):
    """Add a new package to track."""
    pkg = await store.add_package(
        tracking_number=request.tracking_number,
        carrier=request.carrier.value,
        label=request.label,
    )
    if pkg is None:
        raise HTTPException(status_code=409, detail="Package already exists")
    return _build_package_response(pkg)


@app.delete("/api/packages/{tracking_number}", status_code=204)
async def remove_package(tracking_number: str):
    """Remove a tracked package."""
    removed = await store.remove_package(tracking_number)
    if not removed:
        raise HTTPException(status_code=404, detail="Package not found")


@app.post("/api/packages/{tracking_number}/refresh", status_code=202)
async def refresh_package(tracking_number: str):
    """Force an immediate re-scrape of a package."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not running")
    await scheduler.refresh_package(tracking_number)
    return {"status": "refresh_queued"}


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="ok", version=VERSION)


def main():
    """Run the scraper server."""
    import uvicorn

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
