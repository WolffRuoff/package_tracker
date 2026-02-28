"""Tests for the carrier registry and factory."""

from package_tracker.carriers import detect_carrier, get_provider
from package_tracker.carriers.fedex import FedExProvider
from package_tracker.carriers.ups import UPSProvider
from package_tracker.carriers.usps import USPSProvider
from package_tracker.const import Carrier


class TestGetProvider:
    """Tests for get_provider factory."""

    def test_usps_provider(self):
        provider = get_provider(Carrier.USPS, api_key="test_key")
        assert isinstance(provider, USPSProvider)

    def test_ups_provider(self):
        provider = get_provider(Carrier.UPS, client_id="id", client_secret="secret")
        assert isinstance(provider, UPSProvider)

    def test_fedex_provider(self):
        provider = get_provider(Carrier.FEDEX, api_key="key", secret_key="secret")
        assert isinstance(provider, FedExProvider)

    def test_usps_credentials_passed(self):
        provider = get_provider(Carrier.USPS, api_key="my_usps_key")
        assert provider._api_key == "my_usps_key"

    def test_ups_credentials_passed(self):
        provider = get_provider(Carrier.UPS, client_id="my_id", client_secret="my_sec")
        assert provider._client_id == "my_id"
        assert provider._client_secret == "my_sec"

    def test_fedex_credentials_passed(self):
        provider = get_provider(Carrier.FEDEX, api_key="fkey", secret_key="fsec")
        assert provider._api_key == "fkey"
        assert provider._secret_key == "fsec"


class TestDetectCarrier:
    """Tests for detect_carrier auto-detection."""

    def test_detects_usps_numeric(self):
        assert detect_carrier("92001234567890123456") == Carrier.USPS

    def test_detects_usps_service_prefix(self):
        assert detect_carrier("EA123456789US") == Carrier.USPS

    def test_detects_ups(self):
        assert detect_carrier("1Z12345E6605272234") == Carrier.UPS

    def test_detects_fedex_12_digit(self):
        assert detect_carrier("123456789012") == Carrier.FEDEX

    def test_returns_none_for_unknown(self):
        assert detect_carrier("XYZABC") is None

    def test_returns_none_for_empty(self):
        assert detect_carrier("") is None
