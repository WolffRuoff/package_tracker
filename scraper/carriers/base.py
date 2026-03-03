"""Abstract base classes for carrier providers (scraper side)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import Browser, Page

from ..const import DEFAULT_USER_AGENT, Carrier, TrackingStatus

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
        """Use a shared browser instance to fetch fully rendered page HTML."""
        context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(wait_selector, timeout=15000)
            except Exception:
                content = await page.content()
                _LOGGER.error(
                    "Timed out waiting for %r on %s — page content (first 2000 chars):\n%s",
                    wait_selector,
                    url,
                    content[:2000],
                )
                raise
            content = await page.content()
        finally:
            await context.close()
        return content
