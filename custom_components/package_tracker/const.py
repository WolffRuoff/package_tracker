"""Constants for Package Tracker integration."""

from enum import StrEnum

DOMAIN = "package_tracker"

CONF_PACKAGES = "packages"
CONF_AUTO_REMOVE_DAYS = "auto_remove_days"
CONF_SCRAPER_URL = "scraper_url"
DEFAULT_AUTO_REMOVE_DAYS = 1
DEFAULT_SCRAPER_URL = "http://localhost:8230"

DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes
SCAN_INTERVAL_JITTER = 300  # +/- 5 minutes of randomness


class Carrier(StrEnum):
    """Supported shipping carriers."""

    USPS = "usps"
    UPS = "ups"
    FEDEX = "fedex"
    SPEEDX = "speedx"


class TrackingStatus(StrEnum):
    """Package tracking statuses."""

    UNKNOWN = "unknown"
    PRE_TRANSIT = "pre_transit"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    EXPIRED = "expired"
