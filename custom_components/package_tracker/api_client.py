"""Async HTTP client wrapping scraper API calls."""

from __future__ import annotations

import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ScraperApiError(Exception):
    """Error communicating with the scraper API."""


class ScraperApiClient:
    """Client for the package tracker scraper REST API."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def async_health(self) -> dict:
        """Check scraper health. Raises on failure."""
        return await self._get("/api/health")

    async def async_get_packages(self) -> list[dict]:
        """Fetch all packages with tracking results."""
        return await self._get("/api/packages")

    async def async_add_package(
        self, tracking_number: str, carrier: str, label: str
    ) -> dict:
        """Add a package to the scraper."""
        return await self._post(
            "/api/packages",
            json={
                "tracking_number": tracking_number,
                "carrier": carrier,
                "label": label,
            },
        )

    async def async_remove_package(self, tracking_number: str) -> None:
        """Remove a package from the scraper."""
        await self._delete(f"/api/packages/{tracking_number}")

    async def async_refresh_package(self, tracking_number: str) -> dict:
        """Force a re-scrape of a package. Returns updated package data."""
        url = f"{self._base_url}/api/packages/{tracking_number}/refresh"
        try:
            async with self._session.post(
                url, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise ScraperApiError(
                        f"POST /api/packages/{tracking_number}/refresh "
                        f"returned {resp.status}: {text}"
                    )
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ScraperApiError(f"Refresh {tracking_number} failed: {err}") from err

    async def _get(self, path: str) -> dict | list:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise ScraperApiError(
                        f"GET {path} returned {resp.status}: {text}"
                    )
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ScraperApiError(f"GET {path} failed: {err}") from err

    async def _post(self, path: str, json: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.post(
                url, json=json, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise ScraperApiError(
                        f"POST {path} returned {resp.status}: {text}"
                    )
                if resp.content_length and resp.content_length > 0:
                    return await resp.json()
                return {}
        except aiohttp.ClientError as err:
            raise ScraperApiError(f"POST {path} failed: {err}") from err

    async def _delete(self, path: str) -> None:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.delete(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise ScraperApiError(
                        f"DELETE {path} returned {resp.status}: {text}"
                    )
        except aiohttp.ClientError as err:
            raise ScraperApiError(f"DELETE {path} failed: {err}") from err
