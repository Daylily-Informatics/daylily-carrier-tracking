import unittest

from daylily_carrier_tracking.recognition import recognize_tracking_number


class TestRecognition(unittest.TestCase):
    def test_scanner_header_and_presentation_do_not_change_original_scan(self):
        scan = "]C01Z5R89390357567127\r\n"
        recognition = recognize_tracking_number(scan)
        self.assertEqual(recognition.scan, scan)
        self.assertEqual(recognition.status, "identified")
        self.assertEqual(
            [(c.carrier_id, c.tracking_number) for c in recognition.candidates],
            [("ups", "1Z5R89390357567127")],
        )

    def test_fedex_full_label_query_numbers(self):
        labels = {
            "32971514560102447849175802862014": "784917580286",
            "1001921334250001000300779017972697": "779017972697",
            "9622001900000000000000776632517510": "776632517510",
            "9611020987654312345672": "987654312345672",
        }
        for label, number in labels.items():
            with self.subTest(label=label):
                recognition = recognize_tracking_number(label)
                self.assertEqual(recognition.status, "identified")
                self.assertEqual(recognition.candidates[0].tracking_number, number)

    def test_usps_label_excludes_routing_zip(self):
        recognition = recognize_tracking_number("420787459400111206206406260787")
        self.assertEqual(
            [(c.carrier_id, c.tracking_number) for c in recognition.candidates],
            [("usps", "9400111206206406260787")],
        )

    def test_shared_postal_format_does_not_select_the_delivery_carrier(self):
        recognition = recognize_tracking_number("RB123456785GB")
        self.assertEqual(recognition.status, "ambiguous")
        self.assertEqual([c.display_name for c in recognition.candidates], ["Royal Mail Group plc"])

    def test_unrecognized_identifier_round_trips(self):
        scan = "0000-unknown-regional-label"
        recognition = recognize_tracking_number(scan)
        self.assertEqual(recognition.scan, scan)
        self.assertEqual(recognition.status, "unknown")
        self.assertEqual(recognition.candidates, ())

    def test_length_only_dhl_format_requires_operator_choice(self):
        recognition = recognize_tracking_number("60120172242323")
        self.assertEqual(recognition.status, "ambiguous")
        self.assertEqual(recognition.candidates[0].carrier_id, "dhl")

    def test_drops_invalid_check_digit_and_returns_all_valid_carriers(self):
        self.assertEqual(recognize_tracking_number("1Z5R89390357567128").status, "unknown")
        # A valid UPS waybill can also match an Amazon International format.
        recognition = recognize_tracking_number("A0000000000")
        self.assertEqual(recognition.status, "ambiguous")
        self.assertEqual({c.carrier_id for c in recognition.candidates}, {"amazon", "ups"})


if __name__ == "__main__":
    unittest.main()
