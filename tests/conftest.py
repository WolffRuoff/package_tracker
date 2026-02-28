"""Common test fixtures for Package Tracker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from package_tracker.const import (
    CONF_FEDEX_API_KEY,
    CONF_FEDEX_SECRET_KEY,
    CONF_PACKAGES,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_API_KEY,
    DOMAIN,
)


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Return a mock ConfigEntry with all API keys."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_USPS_API_KEY: "test_usps_key",
        CONF_UPS_CLIENT_ID: "test_ups_id",
        CONF_UPS_CLIENT_SECRET: "test_ups_secret",
        CONF_FEDEX_API_KEY: "test_fedex_key",
        CONF_FEDEX_SECRET_KEY: "test_fedex_secret",
    }
    entry.options = {
        CONF_PACKAGES: [
            {
                "label": "Test Package",
                "tracking_number": "92001234567890123456",
                "carrier": "usps",
            }
        ]
    }
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    return entry


@pytest.fixture
def usps_xml_success():
    """Return a successful USPS tracking XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<TrackResponse>
  <TrackInfo ID="92001234567890123456">
    <TrackSummary>
      <Event>Delivered</Event>
      <EventDate>January 15, 2025</EventDate>
      <EventTime>2:30 pm</EventTime>
      <EventCity>Springfield</EventCity>
      <EventState>IL</EventState>
    </TrackSummary>
    <TrackDetail>
      <Event>Out for Delivery</Event>
      <EventDate>January 15, 2025</EventDate>
      <EventTime>8:00 am</EventTime>
      <EventCity>Springfield</EventCity>
      <EventState>IL</EventState>
    </TrackDetail>
    <TrackDetail>
      <Event>Arrived at Post Office</Event>
      <EventDate>January 14, 2025</EventDate>
      <EventTime>6:00 pm</EventTime>
      <EventCity>Springfield</EventCity>
      <EventState>IL</EventState>
    </TrackDetail>
    <ExpectedDeliveryDate>January 15, 2025</ExpectedDeliveryDate>
  </TrackInfo>
</TrackResponse>"""


@pytest.fixture
def usps_xml_error():
    """Return a USPS tracking XML response with an error."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<TrackResponse>
  <TrackInfo ID="INVALID">
    <Error>
      <Number>-2147219283</Number>
      <Description>A valid tracking number was not provided.</Description>
    </Error>
  </TrackInfo>
</TrackResponse>"""


@pytest.fixture
def ups_json_success():
    """Return a successful UPS tracking JSON response."""
    return {
        "trackResponse": {
            "shipment": [
                {
                    "package": [
                        {
                            "currentStatus": {
                                "type": "D",
                                "description": "Delivered",
                            },
                            "deliveryDate": [{"date": "20250115"}],
                            "activity": [
                                {
                                    "status": {
                                        "type": "D",
                                        "description": "Delivered",
                                    },
                                    "location": {
                                        "address": {
                                            "city": "Springfield",
                                            "stateProvince": "IL",
                                            "countryCode": "US",
                                        }
                                    },
                                    "date": "20250115",
                                    "time": "143000",
                                },
                                {
                                    "status": {
                                        "type": "I",
                                        "description": "In Transit",
                                    },
                                    "location": {
                                        "address": {
                                            "city": "Chicago",
                                            "stateProvince": "IL",
                                            "countryCode": "US",
                                        }
                                    },
                                    "date": "20250114",
                                    "time": "080000",
                                },
                            ],
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def ups_token_response():
    """Return a UPS OAuth token response."""
    return {
        "access_token": "test_token_123",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def fedex_json_success():
    """Return a successful FedEx tracking JSON response."""
    return {
        "output": {
            "completeTrackResults": [
                {
                    "trackResults": [
                        {
                            "latestStatusDetail": {
                                "code": "DL",
                                "description": "Delivered",
                            },
                            "estimatedDeliveryTimeWindow": {
                                "window": {
                                    "ends": "2025-01-15T18:00:00Z",
                                }
                            },
                            "scanEvents": [
                                {
                                    "eventDescription": "Delivered",
                                    "derivedStatusCode": "DL",
                                    "scanLocation": {
                                        "city": "Springfield",
                                        "stateOrProvinceCode": "IL",
                                        "countryCode": "US",
                                    },
                                    "date": "2025-01-15T14:30:00Z",
                                },
                                {
                                    "eventDescription": "On FedEx vehicle for delivery",
                                    "derivedStatusCode": "OD",
                                    "scanLocation": {
                                        "city": "Springfield",
                                        "stateOrProvinceCode": "IL",
                                        "countryCode": "US",
                                    },
                                    "date": "2025-01-15T08:00:00Z",
                                },
                            ],
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def fedex_token_response():
    """Return a FedEx OAuth token response."""
    return {
        "access_token": "fedex_token_123",
        "token_type": "bearer",
        "expires_in": 3600,
    }
