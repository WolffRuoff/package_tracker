"""Constants for Package Tracker integration."""

from enum import StrEnum

DOMAIN = "package_tracker"

CONF_USPS_API_KEY = "usps_api_key"
CONF_UPS_CLIENT_ID = "ups_client_id"
CONF_UPS_CLIENT_SECRET = "ups_client_secret"
CONF_FEDEX_API_KEY = "fedex_api_key"
CONF_FEDEX_SECRET_KEY = "fedex_secret_key"
CONF_PACKAGES = "packages"

DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes


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
