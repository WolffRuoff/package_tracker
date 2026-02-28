"""Abstract base classes for carrier providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from ..const import Carrier, TrackingStatus


@dataclass
class TrackingEvent:
    """A single tracking event."""

    timestamp: datetime
    location: str
    description: str
    status: TrackingStatus


@dataclass
class TrackingResult:
    """Result of tracking a package."""

    carrier: Carrier
    tracking_number: str
    status: TrackingStatus = TrackingStatus.UNKNOWN
    estimated_delivery: datetime | None = None
    events: list[TrackingEvent] = field(default_factory=list)
    last_updated: datetime | None = None
    raw_status: str = ""


class CarrierProvider(ABC):
    """Abstract base class for carrier providers."""

    @property
    @abstractmethod
    def carrier_id(self) -> Carrier:
        """Return the carrier identifier."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the carrier display name."""

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Return whether this carrier requires an API key."""

    @abstractmethod
    async def async_track(self, tracking_number: str) -> TrackingResult:
        """Track a package and return the result."""

    @abstractmethod
    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Return True if the tracking number matches this carrier's format."""
