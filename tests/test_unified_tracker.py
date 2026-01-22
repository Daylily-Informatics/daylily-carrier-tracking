import unittest


class TestUnifiedTracker(unittest.TestCase):
    def test_detect_carrier_ups(self):
        from daylily_carrier_tracking.unified_tracker import detect_carrier

        self.assertEqual(detect_carrier("1Z999AA10123456784"), "ups")

    def test_track_usps_not_implemented(self):
        from daylily_carrier_tracking.unified_tracker import UnifiedTracker

        ut = UnifiedTracker(fedex_config={"api_url": "x", "client_id": "x", "client_secret": "x"})
        with self.assertRaises(NotImplementedError):
            ut.track("9400...", carrier="usps")


if __name__ == "__main__":
    unittest.main()
