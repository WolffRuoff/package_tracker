"""Constants for Package Tracker integration."""

from enum import StrEnum

DOMAIN = "package_tracker"

CONF_PACKAGES = "packages"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes
SCAN_INTERVAL_JITTER = 300  # +/- 5 minutes of randomness


class Carrier(StrEnum):
    """Supported shipping carriers."""

    USPS = "usps"
    UPS = "ups"
    FEDEX = "fedex"


class TrackingStatus(StrEnum):
    """Package tracking statuses."""

    UNKNOWN = "unknown"
    PRE_TRANSIT = "pre_transit"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    EXPIRED = "expired"
