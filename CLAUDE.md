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

There are no Python tests, linting, or build steps configured yet.

## Architecture

**Data flow:** Config flow collects API keys → Coordinator creates carrier providers → Coordinator polls all packages every 30 min → Sensor entities expose tracking data → Frontend card auto-discovers `sensor.package_tracker_*` entities.

**Carrier provider pattern:** Abstract `CarrierProvider` in `carriers/base.py` defines the interface. Each carrier (USPS/UPS/FedEx) implements `async_track()` and `validate_tracking_number()`. Adding a new carrier requires: one new file in `carriers/`, one entry in the `CARRIER_PROVIDERS` dict in `carriers/__init__.py`, and updating the `Carrier` enum in `const.py` plus `get_provider()` factory.

**Single coordinator for all packages:** `PackageTrackerCoordinator` in `coordinator.py` polls every carrier for every tracked package in one update cycle. On per-package failure, it retains previous data rather than clearing it.

**Package management via options flow:** One integration config entry holds API keys in `data` and the package list in `options`. Adding/removing packages triggers `_async_update_listener` which reloads the entire integration.

**Embedded frontend:** The Lovelace card JS is served via `hass.http.register_static_path()` in `__init__.py`, so the card ships with the integration—no separate HACS frontend install.

## Key Conventions

- All carrier API calls use `aiohttp` with async/await
- USPS uses XML (ElementTree parsing); UPS and FedEx use JSON REST with OAuth2 token management
- `TrackingResult` and `TrackingEvent` are dataclasses in `carriers/base.py` — all providers return these
- `detect_carrier()` in `carriers/__init__.py` runs each provider's `validate_tracking_number()` to auto-detect carrier from tracking number format
- Frontend uses Lit 3.x with TypeScript decorators (`@customElement`, `@property`, `@state`); strict mode enabled
- Sensor unique IDs follow pattern `package_tracker_{tracking_number}`
- Config keys are defined as `CONF_*` constants in `const.py`
