"""Abstract base classes for carrier providers (scraper side)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus

_LOGGER = logging.getLogger(__name__)


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

    @abstractmethod
    def tracking_url(self, tracking_number: str) -> str:
        """Return the public tracking page URL for a tracking number."""

    @abstractmethod
    async def async_track(
        self, tracking_number: str, browser: Browser
    ) -> TrackingResult:
        """Track a package and return the result."""

    @abstractmethod
    def validate_tracking_number(self, tracking_number: str) -> bool:
        """Return True if the tracking number matches this carrier's format."""

    async def _get_page_content(
        self, browser: Browser, url: str, wait_selector: str
    ) -> str:
        """Fetch fully rendered page HTML via a Camoufox browser context."""
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_selector(wait_selector, timeout=30000)
            content = await page.content()
        finally:
            await context.close()
        return content
