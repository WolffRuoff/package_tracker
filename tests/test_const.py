"""Tests for package_tracker constants."""

from package_tracker.const import Carrier, TrackingStatus


class TestCarrier:
    """Tests for the Carrier enum."""

    def test_usps_value(self):
        assert Carrier.USPS == "usps"

    def test_ups_value(self):
        assert Carrier.UPS == "ups"

    def test_fedex_value(self):
        assert Carrier.FEDEX == "fedex"

    def test_carrier_count(self):
        assert len(Carrier) == 4


class TestTrackingStatus:
    """Tests for the TrackingStatus enum."""

    def test_unknown(self):
        assert TrackingStatus.UNKNOWN == "unknown"

    def test_pre_transit(self):
        assert TrackingStatus.PRE_TRANSIT == "pre_transit"

    def test_in_transit(self):
        assert TrackingStatus.IN_TRANSIT == "in_transit"

    def test_out_for_delivery(self):
        assert TrackingStatus.OUT_FOR_DELIVERY == "out_for_delivery"

    def test_delivered(self):
        assert TrackingStatus.DELIVERED == "delivered"

    def test_exception(self):
        assert TrackingStatus.EXCEPTION == "exception"

    def test_expired(self):
        assert TrackingStatus.EXPIRED == "expired"

    def test_status_count(self):
        assert len(TrackingStatus) == 7
