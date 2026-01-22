import unittest
from unittest.mock import patch
import io
import contextlib


class _DummyUnified:
    def track(self, *args, **kwargs):
        raise NotImplementedError("Carrier 'usps' is not implemented yet.")


class TestCli(unittest.TestCase):
    def test_build_parser_parses_track(self):
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["track", "1Z999AA10123456784", "--carrier", "ups", "--no-raw"])
        self.assertEqual(args.cmd, "track")
        self.assertEqual(args.carrier, "ups")
        self.assertTrue(args.no_raw)

    @patch("daylily_carrier_tracking.cli.UnifiedTracker", autospec=True)
    def test_usps_command_returns_exit_2(self, UT):
        from daylily_carrier_tracking.cli import main

        UT.return_value = _DummyUnified()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = main(["usps", "9400...", "--no-raw"])
        self.assertEqual(rc, 2)
        self.assertIn("not implemented", buf.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
