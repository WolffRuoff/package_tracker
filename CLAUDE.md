# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration (HACS) for tracking shipping packages from USPS, UPS, FedEx, and SpeedX. Two components: a scraper Docker container (`scraper/`) that runs Playwright to scrape carrier pages, and a HACS integration (`custom_components/package_tracker/`) that polls the scraper and exposes sensor entities + Lovelace cards. Domain: `package_tracker`.

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
- **Services as endpoints** — HA services (not HTTP views, not entities) are the chosen mechanism for frontend↔HA communication. `SupportsResponse.ONLY` services act as "API endpoints" callable from the frontend via `callService(..., returnResponse=true)`. New cross-cutting data needs (like carrier lists) should follow this pattern, not introduce new entities or HTTP routes.
- **Scraper is the single source of truth for supported carriers** — `GET /api/carriers` drives both `coordinator.supported_carriers` and the frontend dropdown; no static carrier list exists in the frontend or `services.yaml` at runtime

## Carrier Scraping Strategy

The scraper uses Camoufox (anti-detection Playwright) to scrape carrier tracking pages. **Never suggest switching to official carrier APIs** (USPS Web Tools, UPS Developer, FedEx Web Services, etc.) — they require significant onboarding (business registration, approval processes, credentials management) and are extremely flaky in practice. Web scraping with Camoufox is the intentional long-term approach.

When carriers add bot protection, the correct response is to improve Camoufox configuration or page interaction behavior, not to abandon scraping.

**SpeedX parsing strategy:** SpeedX's tracking page is a Next.js SSR/RSC app. Tailwind CSS class names carry no semantic meaning, so the scraper extracts structured JSON from `self.__next_f.push` script tags instead of CSS selectors. Wait selector: `img[alt='warehouse']`. The JSON is JS-string-escaped (`\"` → `"`), so guard checks use bare word matching (`'trackingNumber' in text`) rather than quoted form, then `str.replace('\\"', '"')` before `json.JSONDecoder().raw_decode()` anchored at the `"events":` array.

**UPS/FedEx parsing strategy:** Both tracking pages are SPAs (UPS: Angular, no `#stApp` container anymore; FedEx: React) that fetch their own data from an internal JSON API. `async_track` intercepts that response via `page.on("response")` — UPS's `webapis.ups.com/track/api/Track/GetStatus` (`trackDetails[0].shipmentProgressActivities` for full history), FedEx's `trackingCal`/`api.fedex.com/track` — rather than scraping the rendered DOM, which is thinner than the API response. DOM parsing is a fallback only, used if the API call is never observed.

## Key Conventions

- `TrackingResult` and `TrackingEvent` are dataclasses defined in **both** `carriers/base.py` (HA side) and `scraper/carriers/base.py` (scraper side) — they are not shared; the HA-side `TrackingResult` has an extra `tracking_url` field populated from the scraper API response
- HA-side carrier providers are stripped to validation + URL only — no scraping, no Playwright, no BeautifulSoup

## Testing Gotchas

- **Never** `from package_tracker.__init__ import` in tests — this creates a separate module in `sys.modules` with a different `__dict__`, breaking `patch("package_tracker.X")`. Use `from package_tracker import` instead.
- Patch the coordinator where it's used: `patch("package_tracker.PackageTrackerCoordinator", return_value=mock_coord)`. Set `mock_coord.async_config_entry_first_refresh = AsyncMock()` inside the patch context.
- Service handler tests call `handle_add_package(hass, call)` / `handle_refresh_packages(hass, call)` / `handle_get_carriers(hass, call)` directly with a mock coordinator in `hass.data[DOMAIN]` — no need for `_setup_entry` helpers.
- Setup/unload tests patch `register_services`/`unregister_services` at the module level (`patch("package_tracker.register_services")`).
- Coordinator fixtures created via `__new__` (bypassing `__init__`) must manually set `coord.supported_carriers = []`. The `mock_scraper_api` conftest fixture includes a default `async_get_carriers` return value.
