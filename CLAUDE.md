# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration (HACS) for tracking shipping packages from USPS, UPS, and FedEx. Split into two components:

1. **Scraper container** (`scraper/`) — standalone Docker app running Playwright + Chromium, scrapes carrier pages, exposes results via REST API
2. **HACS integration** (`custom_components/package_tracker/`) — lightweight HA integration (no browser deps) that polls the scraper API and exposes sensor entities + Lovelace card

Domain: `package_tracker`.

## Architecture

```
HA Config Flow ──┐
HA Service ──────┼──► Scraper API (add/remove packages)
                 │         │
                 │    Scraper polls carriers
                 │    every ~30min via Playwright
                 │         │
HA Coordinator ◄──────── GET /api/packages (polling)
       │
   Sensor Entities + Lovelace Cards
```

- **HA is the UI layer** — users manage packages via HA config flow OR the `add_package` service, both of which forward to the scraper
- **Scraper is the data layer** — owns the package list in SQLite, runs the polling scheduler, caches results
- **Communication** — HA coordinator polls `GET /api/packages` on a 30-min jittered interval
- **`add_package` service** — registered once per domain in `async_setup_entry`, removed in `async_unload_entry` when the last entry is gone; reuses the coordinator's persistent `aiohttp` session via `coord._ensure_client()`

## Build Commands

First-time setup (installs uv if missing, Python 3.12, and all deps):
```bash
make setup
```

Individual targets:
```bash
make install          # uv sync for HA integration (includes dev deps)
make install-scraper  # uv sync for scraper (includes dev deps)
make test             # Run HA integration tests
make test-scraper     # Run scraper tests
make test-all         # Run all tests
make coverage         # Run tests with coverage
make lint             # Run linter
make build-card       # Build frontend Lovelace card
make docker-build     # Build scraper Docker image
make docker-run       # Run scraper container locally
make docker-stop      # Stop scraper container
```

## Scraper Container (`scraper/`)

FastAPI app on port 8230 (configurable via `PORT` env var). SQLite DB at `/data/package_tracker.db` (Docker volume). Docker Hub image: `wolffruoff/package-tracker-scraper`.

**REST API:**
- `GET /api/packages` — all packages with latest tracking results
- `POST /api/packages` — add package `{tracking_number, carrier, label}`
- `DELETE /api/packages/{tracking_number}` — remove package
- `POST /api/packages/{tracking_number}/refresh` — force re-scrape
- `GET /api/health` — health check

**Carrier provider pattern (scraper side):** Abstract `CarrierProvider` in `scraper/carriers/base.py`. Each carrier implements `async_track(tracking_number, browser)`, `validate_tracking_number()`, and `tracking_url()`. The base class provides `_get_page_content(browser, url, wait_selector)` using a shared Playwright browser instance. Each carrier's `_parse_tracking_page(html, result)` uses BeautifulSoup.

**Scheduler:** Background asyncio task, 30-min interval with ±5-min jitter. Browser launched once at startup via FastAPI lifespan, reused across all scrapes.

## HACS Integration (`custom_components/package_tracker/`)

**No browser dependencies** — requirements list is empty. Communicates with scraper via `api_client.py` (wraps aiohttp calls).

**Config flow:** Initial setup collects scraper URL, validates via `GET /api/health`. Config version 2. Options flow forwards add/remove to scraper API.

**Coordinator:** Polls `GET /api/packages` from scraper, parses JSON into `TrackingResult` objects. Keeps jittered interval and delivered auto-removal logic HA-side. `_ensure_client()` returns the shared `ScraperApiClient` — use it instead of creating a new `aiohttp.ClientSession`.

**`add_package` service:** Defined in `__init__.py`. Schema: `tracking_number` (required), `label` (required), `carrier` (optional, auto-detected via `detect_carrier()` if blank). Documented via `services.yaml` so HA Dev Tools shows full field descriptions. Registered once per domain; removed when the last config entry is unloaded.

**Carrier providers (HA side):** Stripped to validation + URL only. No scraping, no Playwright, no BeautifulSoup. Used for `detect_carrier()` auto-detection and tracking URL generation.

**Frontend cards:** Two Lit 3.x cards in `frontend-src/src/`:
- `package-tracker-card.ts` — displays all tracked sensors; has a visual editor (`package-tracker-card-editor`)
- `package-tracker-add-card.ts` — form card for adding packages via the `add_package` service; has a visual editor (`package-tracker-add-card-editor`) for the `title` field

## Testing

**HA integration tests** (`tests/`): Uses `pytest` + `pytest-asyncio`. Mock `aiohttp` responses via `mock_scraper_api` fixture. Carrier tests cover validation + URL only. `test_init.py` covers the `add_package` service registration, unload cleanup, and handler behavior.

**Scraper tests** (`scraper/tests/`): Uses `pytest` + `pytest-asyncio`. HTML fixtures in `scraper/tests/fixtures/`. Storage tests use in-memory SQLite. API tests use `httpx` `AsyncClient` with FastAPI's ASGI transport.

## CI/CD

- **`validate.yml`** — runs on PRs and pushes to `main`. Two jobs: HACS validation (`hacs/action@main`) and tests (`pytest` with Codecov upload).
- **`release.yml`** — runs on pushes to `main`. Auto-determines version bump from conventional commits (`feat:` → minor, `BREAKING CHANGE` → major, else patch). Updates `manifest.json` version, creates a git tag + GitHub Release, then builds and pushes the scraper Docker image to `wolffruoff/package-tracker-scraper` on Docker Hub (tagged `latest` + version).

## Key Conventions

- `TrackingResult` and `TrackingEvent` are dataclasses — defined in both `carriers/base.py` (HA side) and `scraper/carriers/base.py` (scraper side)
- HA-side `TrackingResult` has an extra `tracking_url` field populated from scraper API response
- `detect_carrier()` in `carriers/__init__.py` runs each provider's `validate_tracking_number()` to auto-detect carrier
- Frontend uses Lit 3.x with TypeScript decorators; strict mode enabled
- Sensor unique IDs: `package_tracker_{tracking_number}`
- Sensor `extra_state_attributes` includes `tracking_url` from scraper API
- `services.yaml` in the integration directory makes the `add_package` service visible with full field docs in HA Developer Tools

## Testing Gotchas

- **Never** `from package_tracker.__init__ import` in tests — this creates a separate module in `sys.modules` with a different `__dict__`, breaking `patch("package_tracker.X")`. Use `from package_tracker import` instead.
- Patch the coordinator where it's used: `patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coord)`. Set `mock_coord.async_config_entry_first_refresh = AsyncMock()` inside the patch context.
- Service handler is captured after `async_setup_entry` via `mock_hass.services.async_register.call_args[0][2]`.
