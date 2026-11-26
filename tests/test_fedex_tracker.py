import unittest
from unittest.mock import patch


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class TestFedexTracker(unittest.TestCase):
    def _cfg(self):
        return {
            "api_url": "https://apis.fedex.com/oauth/token",
            "client_id": "id",
            "client_secret": "secret",
            "track_url": "https://apis.fedex.com/track/v1/trackingnumbers",
            "ship_track_url": "https://apis.fedex.com/ship/v1/trackingnumbers",
        }

    def test_normalize_valid_minimal(self):
        from daylily_carrier_tracking.fedex_tracker import normalize_fedex_track_ops_meta

        raw = {
            "output": {
                "completeTrackResults": [
                    {
                        "trackResults": [
                            {
                                "latestStatusDetail": {"statusByLocale": "Delivered"},
                                "dateAndTimes": [
                                    {"type": "ACTUAL_DELIVERY", "dateTime": "2023-06-27T11:34:00+00:00"},
                                    {"type": "SHIP", "dateTime": "2023-06-26T00:00:00-06:00"},
                                ],
                                "originLocation": {
                                    "locationContactAndAddress": {"address": {"stateOrProvinceCode": "CA", "city": "VALENCIA"}}
                                },
                                "lastUpdatedDestinationAddress": {"stateOrProvinceCode": "CA", "city": "OAKLAND"},
                                "serviceDetail": {"shortDescription": "P-2"},
                            }
                        ]
                    }
                ]
            }
        }

        ops = normalize_fedex_track_ops_meta(raw)
        self.assertEqual(ops["Delivery_Status"], "Delivered")
        self.assertEqual(ops["Origin_state"], "CA")
        self.assertEqual(ops["Destination_state"], "CA")
        self.assertEqual(ops["Delivery_weekday"], "Tuesday")
        self.assertTrue(isinstance(ops["Transit_Time_sec"], (int, float)))
        self.assertGreater(ops["Transit_Time_sec"], 0)
        self.assertEqual(ops["Destination_state_alt"], "P-2")

    def test_normalize_notfound_matches_readme_defaults(self):
        from daylily_carrier_tracking.fedex_tracker import normalize_fedex_track_ops_meta

        raw = {
            "output": {
                "completeTrackResults": [
                    {"trackResults": [{"error": {"code": "TRACKING.TRACKINGNUMBER.NOTFOUND"}}]}
                ]
            }
        }
        ops = normalize_fedex_track_ops_meta(raw)
        self.assertEqual(ops["Delivery_Status"], "na")
        self.assertEqual(ops["Origin_state"], "na")
        self.assertEqual(ops["Destination_state"], "na")
        self.assertEqual(ops["Transit_Time_sec"], -1)

    @patch("daylily_carrier_tracking.fedex_tracker.requests.post")
    def test_not_found_is_a_failed_lookup(self, post):
        from daylily_carrier_tracking import UnifiedTracker

        oauth_ok = _Resp(200, {"access_token": "tok", "expires_in": 3600})
        track_notfound = _Resp(
            200,
            {
                "output": {
                    "completeTrackResults": [
                        {"trackResults": [{"error": {"code": "TRACKING.TRACKINGNUMBER.NOTFOUND"}}]}
                    ]
                }
            },
        )
        post.side_effect = [oauth_ok, track_notfound]
        result = UnifiedTracker(fedex_config=self._cfg()).track("X", carrier="fedex")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "not_found")
        self.assertNotIn("ops_meta", result)
        self.assertEqual(post.call_count, 2)

    @patch("daylily_carrier_tracking.fedex_tracker.requests.post")
    def test_explicit_ship_endpoint(self, post):
        from daylily_carrier_tracking import FedexTracker

        oauth_ok = _Resp(200, {"access_token": "tok", "expires_in": 3600})
        ship_ok = _Resp(
            200,
            {
                "output": {
                    "completeTrackResults": [
                        {
                            "trackResults": [
                                {
                                    "latestStatusDetail": {"statusByLocale": "Delivered"},
                                    "dateAndTimes": [{"type": "ACTUAL_DELIVERY", "dateTime": "2023-06-27T11:34:00+00:00"}],
                                    "originLocation": {
                                        "locationContactAndAddress": {"address": {"stateOrProvinceCode": "CA", "city": "VALENCIA"}}
                                    },
                                    "lastUpdatedDestinationAddress": {"stateOrProvinceCode": "CA", "city": "OAKLAND"},
                                }
                            ]
                        }
                    ]
                }
            },
        )

        post.side_effect = [oauth_ok, ship_ok]

        tracker = FedexTracker(config=self._cfg())
        out = tracker.track("X", api_preference="ship", include_raw=False)
        self.assertEqual(out["source"]["api"], "ship_v1")
        self.assertEqual(out["ops_meta"]["Delivery_Status"], "Delivered")

    @patch("daylily_carrier_tracking.fedex_tracker.requests.post")
    def test_lookup_keeps_mismatched_observations_out_of_result(self, post):
        from daylily_carrier_tracking import UnifiedTracker

        post.side_effect = [
            _Resp(200, {"access_token": "tok"}),
            _Resp(200, {"output": {"completeTrackResults": [{"trackResults": [
                {"trackingNumberInfo": {"trackingNumber": "DIFFERENT"}}
            ]}]}}),
        ]
        result = UnifiedTracker(fedex_config=self._cfg()).track("X", carrier="fedex")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "invalid_response")
        self.assertNotIn("ops_meta", result)


if __name__ == "__main__":
    unittest.main()
