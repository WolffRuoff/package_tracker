# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration (HACS) for tracking shipping packages from USPS, UPS, and FedEx. Combines a Python backend (HA integration) with a TypeScript frontend (Lovelace card). Domain: `package_tracker`.

## Build Commands

**Frontend card** (from `frontend-src/`):
```bash
cd frontend-src && npm install && npm run build
```
This compiles TypeScript → `custom_components/package_tracker/frontend/package-tracker-card.js` via Rollup.

**HACS validation** (CI runs automatically on push/PR to main):
```bash
# Locally via the HACS action container, or just push and check GitHub Actions
```

**Tests** (from repo root):
```bash
pip install -e ".[test]"
playwright install chromium
pytest --cov
```

## Architecture

**Data flow:** Config flow (no API keys required) → Coordinator creates all carrier providers → Coordinator scrapes carrier tracking pages every ~30 min (with jitter) → Sensor entities expose tracking data → Frontend card auto-discovers `sensor.package_tracker_*` entities.

**Carrier provider pattern:** Abstract `CarrierProvider` in `carriers/base.py` defines the interface. Each carrier (USPS/UPS/FedEx) implements `async_track()`, `validate_tracking_number()`, and `tracking_url()`. The base class provides `_get_page_content(url, wait_selector)` which uses Playwright (headless Chromium) to fetch fully rendered page HTML. Each carrier's `_parse_tracking_page(html, result)` uses BeautifulSoup to extract status, events, and delivery dates from the rendered HTML. Adding a new carrier requires: one new file in `carriers/`, one entry in the `CARRIER_PROVIDERS` dict in `carriers/__init__.py`, and updating the `Carrier` enum in `const.py`.

**Web scraping approach:** No API keys needed. Each carrier provider navigates to the carrier's public tracking page, waits for tracking content to render (handles JS-rendered SPAs), then parses the HTML. A randomized scan interval (±5 min jitter around 30 min) avoids bot-like request patterns.

**Single coordinator for all packages:** `PackageTrackerCoordinator` in `coordinator.py` polls every carrier for every tracked package in one update cycle. On per-package failure, it retains previous data rather than clearing it.

**Package management via options flow:** One integration config entry holds an empty `data` dict and the package list in `options`. Adding/removing packages triggers `_async_update_listener` which reloads the entire integration.

**Embedded frontend:** The Lovelace card JS is served via `hass.http.register_static_path()` in `__init__.py`, so the card ships with the integration—no separate HACS frontend install. Each package row includes a "view on website" link that opens the carrier's tracking page in a new tab.

## Testing

Tests live in `tests/` at the repo root. Uses `pytest` + `pytest-asyncio`. Carrier tracking page HTML fixtures are stored in `tests/fixtures/{usps,ups,fedex}/` — tests parse these directly via `_parse_tracking_page()` and mock Playwright at the browser level for `async_track()` tests.

## Key Conventions

- All carrier tracking uses Playwright (headless Chromium) + BeautifulSoup for web scraping
- `TrackingResult` and `TrackingEvent` are dataclasses in `carriers/base.py` — all providers return these
- `detect_carrier()` in `carriers/__init__.py` runs each provider's `validate_tracking_number()` to auto-detect carrier from tracking number format
- Frontend uses Lit 3.x with TypeScript decorators (`@customElement`, `@property`, `@state`); strict mode enabled
- Sensor unique IDs follow pattern `package_tracker_{tracking_number}`
- Sensor `extra_state_attributes` includes `tracking_url` for the carrier's public tracking page
