# Package Tracker for Home Assistant

[![coverage](https://raw.githubusercontent.com/WolffRuoff/package_tracker/main/coverage.svg)](https://github.com/WolffRuoff/package_tracker)
[![Docker Image Version](https://img.shields.io/docker/v/wolffruoff/package-tracker-scraper?label=scraper)](https://hub.docker.com/r/wolffruoff/package-tracker-scraper)

A HACS custom integration that tracks shipping packages from USPS, UPS, FedEx, and SpeedX with a built-in Lovelace card.

## Features

- Track packages from **USPS**, **UPS**, **FedEx**, and **SpeedX**
- Auto-detect carrier from tracking number format
- Built-in Lovelace card with status icons and color coding
- Add/remove packages via the UI options flow or the `add_package` service
- Add Package Lovelace card — form card for adding packages directly from the dashboard
- Modular carrier system — easy to extend with new carriers

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **3-dot menu** → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Install "Package Tracker"
5. Restart Home Assistant

### Manual

1. Copy `custom_components/package_tracker/` to your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

This integration has two components: a **scraper container** that fetches tracking data, and a **HACS integration** that displays it in Home Assistant.

### 1. Deploy the Scraper Container

Run the scraper as a Docker container on your network (e.g. on the same host as Home Assistant):

```yaml
# docker-compose.yml
services:
  scraper:
    image: wolffruoff/package-tracker-scraper:latest
    container_name: package-tracker-scraper
    ports:
      - "8230:8230"
    volumes:
      - scraper-data:/data
    environment:
      - PORT=8230
      - DB_PATH=/data/package_tracker.db
    restart: unless-stopped

volumes:
  scraper-data:
```

```bash
docker compose up -d
```

### 2. Install the HACS Integration

Follow the [Installation](#installation) steps above.

### 3. Connect to the Scraper

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Package Tracker"
3. Enter the scraper URL (e.g. `http://localhost:8230`)

### 4. Add the Dashboard Resource

The Lovelace cards are served as a static file by HA. Register the resource so dashboards can load it:

1. Go to **Settings** → **Dashboards** → **3-dot menu** → **Resources**
2. Click **Add Resource**
3. Set the URL to `/package_tracker/package-tracker-card.js`
4. Set the resource type to **JavaScript module**
5. Click **Create**

> After a manual install the resource must be added manually. HACS installs may handle this automatically.

## Adding Packages

### Via the UI options flow

1. Go to the Package Tracker integration
2. Click **Configure**
3. Select **Add a package**
4. Enter a label, tracking number, and optionally select the carrier (auto-detected by default)

### Via the `add_package` service

Call `package_tracker.add_package` from Developer Tools → Services or an automation:

```yaml
service: package_tracker.add_package
data:
  tracking_number: "92001234567890123456"
  label: "Amazon Order"
  carrier: ""   # leave blank to auto-detect
```

Fields: `tracking_number` (required), `label` (required), `carrier` (optional — `usps`, `ups`, `fedex`, `speedx`, or blank for auto-detect).

### Via the Add Package card

Add `custom:package-tracker-add-card` to any dashboard for a form-based UI (see [Lovelace Cards](#lovelace-cards)).

## Lovelace Cards

### Package Tracker Card

Displays all tracked packages sorted by status priority:

```yaml
type: custom:package-tracker-card
title: My Packages
show_delivered: true
```

The card auto-discovers all `sensor.package_tracker_*` entities.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | "Package Tracker" | Card title |
| `show_delivered` | boolean | true | Show delivered packages |

### Add Package Card

A form card for adding packages without leaving the dashboard. Supports the visual editor in the card picker.

```yaml
type: custom:package-tracker-add-card
title: Add Package
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | "Add Package" | Card title |

## Sensor Attributes

Each tracked package creates a sensor with these attributes:

- `label` — Package label
- `carrier` — Carrier name (usps/ups/fedex/speedx)
- `tracking_number` — Tracking number
- `estimated_delivery` — Estimated delivery date (ISO format)
- `last_updated` — Last successful API poll (ISO format)
- `raw_status` — Raw status text from the carrier
- `tracking_url` — Direct link to the carrier's tracking page
- `events` — List of tracking events with timestamp, location, description, and status

## Development / Testing

First-time setup (installs uv, Python 3.12, and all dependencies):

```bash
make setup
```

Run tests:

```bash
make test           # HA integration tests
make test-scraper   # Scraper tests
make test-all       # Both
make coverage       # Tests with coverage
```

CI requires all tests to pass before merging.
