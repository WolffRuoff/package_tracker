"""Abstract base classes for carrier providers (scraper side)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import Browser

from ..const import Carrier, TrackingStatus
from ..util import parse_date

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


def _identify_bot_service(url: str, html: str, headers: dict[str, str]) -> str:
    """Identify which bot-protection service is blocking the page, if any."""
    url_l = url.lower()
    html_l = html.lower()
    headers_l = {k.lower(): v for k, v in headers.items()}

    if (
        "datadome" in url_l
        or "captcha-delivery.com" in url_l
        or any("x-dd-" in k for k in headers_l)
        or "datadome" in html_l
    ):
        return "DataDome"

    if (
        "akamai" in url_l
        or any("akamai" in k for k in headers_l)
        or "_akamai" in html_l
        or "akam.net" in html_l
    ):
        return "Akamai Bot Manager"

    if "_kpsdk" in html_l or "kpsdk" in html_l or "ips.js" in html_l:
        return "Kasada"

    if (
        "cloudflare" in url_l
        or headers_l.get("server", "").lower() == "cloudflare"
        or "just a moment" in html_l
        or "__cf_bm" in html_l
    ):
        return "Cloudflare"

    if "imperva" in url_l or "incapsula" in html_l or "_Incapsula_Resource" in html_l:
        return "Imperva/Incapsula"

    if "perimeterx" in html_l or "_pxdk" in html_l:
        return "PerimeterX"

    return "unknown"


_BOT_HEADER_KEYWORDS = ("bot", "akamai", "datadome", "kasada", "cf-", "x-dd", "server", "via", "x-cache")


# Free-text status phrases shared by the HTML-scraping carriers (USPS/UPS/FedEx),
# matched as case-insensitive substrings. Ordered specific-first. SpeedX does not
# use this — it maps structured category codes and overrides _map_status.
STATUS_MAPPING: dict[str, TrackingStatus] = {
    "delivered": TrackingStatus.DELIVERED,
    "on fedex vehicle for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "out for delivery": TrackingStatus.OUT_FOR_DELIVERY,
    "moving through network": TrackingStatus.IN_TRANSIT,
    "on the way": TrackingStatus.IN_TRANSIT,
    "preparing for delivery": TrackingStatus.IN_TRANSIT,
    "at local fedex facility": TrackingStatus.IN_TRANSIT,
    "at destination sort facility": TrackingStatus.IN_TRANSIT,
    "in transit": TrackingStatus.IN_TRANSIT,
    "arrived": TrackingStatus.IN_TRANSIT,
    "departed": TrackingStatus.IN_TRANSIT,
    "shipment information sent to fedex": TrackingStatus.PRE_TRANSIT,
    "shipper created a label": TrackingStatus.PRE_TRANSIT,
    "shipping label created": TrackingStatus.PRE_TRANSIT,
    "label created": TrackingStatus.PRE_TRANSIT,
    "order processed": TrackingStatus.PRE_TRANSIT,
    "picked up": TrackingStatus.PRE_TRANSIT,
    "pickup": TrackingStatus.PRE_TRANSIT,
    "pre-shipment": TrackingStatus.PRE_TRANSIT,
    "accepted": TrackingStatus.PRE_TRANSIT,
    "delivery exception": TrackingStatus.EXCEPTION,
    "delivery attempt": TrackingStatus.EXCEPTION,
    "returned to sender": TrackingStatus.EXCEPTION,
    "clearance delay": TrackingStatus.EXCEPTION,
    "notice left": TrackingStatus.EXCEPTION,
    "exception": TrackingStatus.EXCEPTION,
    "alert": TrackingStatus.EXCEPTION,
}


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

    def _map_status(self, raw_status: str) -> TrackingStatus:
        """Map a free-text status string to a TrackingStatus via substring match."""
        lower = raw_status.lower()
        for key, status in STATUS_MAPPING.items():
            if key in lower:
                return status
        return TrackingStatus.UNKNOWN

    def _parse_date(self, text: str) -> datetime | None:
        """Parse a carrier date/time string into a naive datetime, or None."""
        return parse_date(text)

    async def _get_page_content(
        self, browser: Browser, url: str, wait_selector: str
    ) -> str:
        """Fetch fully rendered page HTML via a Camoufox browser context."""
        context = await browser.new_context()
        page = await context.new_page()

        _response_headers: dict[str, str] = {}

        async def _on_response(response) -> None:
            nonlocal _response_headers
            if not _response_headers:
                try:
                    _response_headers = await response.all_headers()
                except Exception:
                    pass

        page.on("response", _on_response)

        tracking_number_hint = url.split("=")[-1].split("/")[-1][:30]

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector(wait_selector, timeout=45000)
            return await page.content()
        except Exception:
            current_url = page.url
            try:
                title = await page.title()
                raw_html = await page.content()
            except Exception:
                title = "(unavailable)"
                raw_html = ""

            bot = _identify_bot_service(current_url, raw_html, _response_headers)
            relevant_headers = {
                k: v
                for k, v in _response_headers.items()
                if any(kw in k.lower() for kw in _BOT_HEADER_KEYWORDS)
            }

            dump_path = f"/tmp/page_fail_{tracking_number_hint}.html"
            try:
                with open(dump_path, "w") as f:
                    f.write(raw_html)
            except Exception:
                dump_path = "(write failed)"

            _LOGGER.error(
                "Page load failed for %s\n"
                "  selector=%r  redirected_to=%s\n"
                "  page_title=%r  bot_service=%s\n"
                "  relevant_headers=%s\n"
                "  full HTML dumped to %s\n"
                "  page_body[:2000]:\n%s",
                url,
                wait_selector,
                current_url if current_url != url else "(none)",
                title,
                bot,
                relevant_headers,
                dump_path,
                raw_html[:2000],
            )
            raise
        finally:
            await context.close()
