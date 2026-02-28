# Package Tracker for Home Assistant

A HACS custom integration that tracks shipping packages from USPS, UPS, and FedEx with a built-in Lovelace card.

## Features

- Track packages from **USPS**, **UPS**, and **FedEx**
- Auto-detect carrier from tracking number format
- Built-in Lovelace card with status icons and color coding
- Add/remove packages via the UI options flow
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

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Package Tracker"
3. Enter your API keys for the carriers you want to use (leave blank to skip)

### Getting API Keys

| Carrier | Portal | Notes |
|---------|--------|-------|
| USPS | [Web Tools Registration](https://www.usps.com/business/web-tools-apis/) | Free User ID |
| UPS | [UPS Developer Portal](https://developer.ups.com/) | OAuth Client ID + Secret |
| FedEx | [FedEx Developer Portal](https://developer.fedex.com/) | API Key + Secret Key |

## Adding Packages

1. Go to the Package Tracker integration
2. Click **Configure**
3. Select **Add a package**
4. Enter a label, tracking number, and optionally select the carrier (auto-detected by default)

## Lovelace Card

Add the card to your dashboard:

```yaml
type: custom:package-tracker-card
title: My Packages
show_delivered: true
```

The card auto-discovers all `sensor.package_tracker_*` entities and displays them sorted by status priority.

### Card Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | "Package Tracker" | Card title |
| `show_delivered` | boolean | true | Show delivered packages |

## Sensor Attributes

Each tracked package creates a sensor with these attributes:

- `label` — Package label
- `carrier` — Carrier name (usps/ups/fedex)
- `tracking_number` — Tracking number
- `estimated_delivery` — Estimated delivery date (ISO format)
- `last_updated` — Last successful API poll (ISO format)
- `raw_status` — Raw status text from the carrier
- `events` — List of tracking events with timestamp, location, description, and status
