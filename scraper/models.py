"""Pydantic models for the scraper REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .const import Carrier, TrackingStatus


class AddPackageRequest(BaseModel):
    """Request body for adding a package."""

    tracking_number: str
    carrier: Carrier
    label: str


class TrackingEventResponse(BaseModel):
    """A single tracking event in the API response."""

    timestamp: str
    location: str
    description: str
    status: TrackingStatus


class PackageResponse(BaseModel):
    """A package with its latest tracking result."""

    tracking_number: str
    carrier: Carrier
    label: str
    created_at: str
    status: TrackingStatus
    raw_status: str
    estimated_delivery: str | None
    last_updated: str | None
    tracking_url: str | None
    events: list[TrackingEventResponse]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
