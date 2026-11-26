import unittest
from unittest.mock import patch

from daylily_carrier_tracking import UnifiedTracker


class TestUnifiedTracker(unittest.TestCase):
    @patch("daylily_carrier_tracking.unified_tracker.FedexTracker")
    def test_unknown_scan_never_loads_fedex(self, fedex):
        result = UnifiedTracker(fedex_enabled=True).track("000REGIONAL")
        self.assertEqual(result["status"], "not_attempted")
        self.assertEqual(result["reason"], "carrier_unknown")
        self.assertEqual(result["tracking_number"], "000REGIONAL")
        fedex.assert_not_called()

    @patch("daylily_carrier_tracking.unified_tracker.FedexTracker")
    def test_unsupported_lookup_has_no_placeholder_observations(self, fedex):
        result = UnifiedTracker().track_ops_meta("000REGIONAL", carrier="usps")
        self.assertEqual(result["status"], "not_attempted")
        self.assertEqual(result["reason"], "lookup_unsupported")
        self.assertEqual(result["carrier"], "usps")
        self.assertNotIn("ops_meta", result)
        fedex.assert_not_called()

    @patch("daylily_carrier_tracking.unified_tracker.FedexTracker")
    def test_manual_fedex_selection_preserves_unknown_identifier(self, fedex):
        fedex.return_value.track.return_value = {"carrier": "fedex", "tracking_number": "000REGIONAL", "ops_meta": {}}
        result = UnifiedTracker(fedex_enabled=True).track("000REGIONAL", carrier="FedEx", include_raw=False)
        self.assertEqual(result["status"], "succeeded")
        fedex.return_value.track.assert_called_once_with("000REGIONAL", include_raw=False, api_preference="track")

    @patch("daylily_carrier_tracking.unified_tracker.FedexTracker")
    def test_explicit_disable_wins_over_supplied_config(self, fedex):
        result = UnifiedTracker(fedex_enabled=False, fedex_config={}).track("000REGIONAL", carrier="fedex")
        self.assertEqual(result["reason"], "lookup_disabled")
        fedex.assert_not_called()

    def test_missing_credentials_report_skipped(self):
        result = UnifiedTracker(fedex_config={}).track("000REGIONAL", carrier="fedex")
        self.assertEqual(result["status"], "not_attempted")
        self.assertEqual(result["reason"], "configuration_error")


if __name__ == "__main__":
    unittest.main()
