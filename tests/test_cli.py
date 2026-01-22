import unittest
from unittest.mock import patch
import io
import contextlib
import tempfile
from pathlib import Path
import json


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

    def test_build_parser_parses_track_pretty_after_subcommand(self):
        # Regression: allow `tday track ... --pretty` (not just `tday --pretty track ...`).
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["track", "123456789012", "--carrier", "fedex", "--pretty"])
        self.assertEqual(args.cmd, "track")
        self.assertEqual(args.carrier, "fedex")
        self.assertTrue(args.pretty)

    def test_build_parser_parses_track_pretty_before_subcommand(self):
        # Back-compat: `tday --pretty track ...` should still work.
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["--pretty", "track", "123456789012", "--carrier", "fedex"])
        self.assertEqual(args.cmd, "track")
        self.assertTrue(args.pretty)

    def test_build_parser_parses_test_subcommand(self):
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["test", "--test-fedex"])
        self.assertEqual(args.cmd, "test")
        self.assertTrue(args.test_fedex)

    def test_build_parser_parses_doctor(self):
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["doctor", "--no-network"])
        self.assertEqual(args.cmd, "doctor")
        self.assertTrue(args.no_network)

    def test_build_parser_parses_doctor_json(self):
        from daylily_carrier_tracking.cli import build_parser

        args = build_parser().parse_args(["doctor", "--carrier", "ups", "--json"])
        self.assertEqual(args.cmd, "doctor")
        self.assertTrue(args.json)
        self.assertEqual(args.carrier, "ups")

    def test_main_doctor_no_network_with_config_path_returns_0(self):
        # Ensure doctor can validate config + exit cleanly without network.
        from daylily_carrier_tracking.cli import main

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fedex_prod.yaml"
            p.write_text(
                "api_url: https://apis.fedex.com/oauth/token\nclient_id: abc\nclient_secret: def\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = main(["doctor", "--config-path", str(p), "--no-network"])
            self.assertEqual(rc, 0)

    def test_main_doctor_json_writes_stdout_not_stderr(self):
        from daylily_carrier_tracking.cli import main

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fedex_prod.yaml"
            p.write_text(
                "api_url: https://apis.fedex.com/oauth/token\nclient_id: abc\nclient_secret: def\n",
                encoding="utf-8",
            )
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["doctor", "--config-path", str(p), "--no-network", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err.getvalue(), "")
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["carrier"]["effective"], "fedex")
            self.assertIn("python", payload)
            self.assertIn("config", payload)

    def test_main_doctor_json_ups_works_without_config(self):
        from daylily_carrier_tracking.cli import main

        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["doctor", "--carrier", "ups", "--env", "prod", "--json"])
        self.assertEqual(rc, 2)
        self.assertEqual(err.getvalue(), "")
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["carrier"]["effective"], "ups")

    def test_main_doctor_json_ups_valid_config_returns_0(self):
        from daylily_carrier_tracking.cli import main

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ups_prod.yaml"
            p.write_text("client_id: abc\nclient_secret: def\n", encoding="utf-8")

            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["doctor", "--carrier", "ups", "--config-path", str(p), "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err.getvalue(), "")
            payload = json.loads(out.getvalue())
            self.assertTrue(payload["config"]["valid"])

    def test_main_doctor_carrier_auto_requires_tracking_number(self):
        from daylily_carrier_tracking.cli import main

        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["doctor", "--carrier", "auto", "--json"])
        self.assertEqual(rc, 2)
        self.assertEqual(err.getvalue(), "")
        payload = json.loads(out.getvalue())
        self.assertIn("error", payload)

    @patch("daylily_carrier_tracking.cli.subprocess.run", autospec=True)
    def test_main_test_runs_unittest_discover(self, run):
        from daylily_carrier_tracking.cli import main

        run.return_value.returncode = 0
        rc = main(["test"])
        self.assertEqual(rc, 0)
        called = run.call_args[0][0]
        # argv[0] is sys.executable; just assert the unittest invocation shape.
        self.assertIn("-m", called)
        self.assertIn("unittest", called)
        self.assertIn("discover", called)
        self.assertIn("tests", called)

    @patch("daylily_carrier_tracking.cli.UnifiedTracker", autospec=True)
    def test_usps_command_returns_exit_2(self, UT):
        from daylily_carrier_tracking.cli import main

        UT.return_value = _DummyUnified()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = main(["usps", "9400...", "--no-raw"])
        self.assertEqual(rc, 2)
        self.assertIn("not implemented", buf.getvalue().lower())

    def test_unified_tracker_does_not_require_fedex_config_for_ups(self):
        # Regression: UnifiedTracker should not eagerly construct FedexTracker
        # when calling track() for an unimplemented carrier.
        from daylily_carrier_tracking.unified_tracker import UnifiedTracker

        with patch("daylily_carrier_tracking.unified_tracker.FedexTracker", autospec=True) as FT:
            FT.side_effect = AssertionError("FedexTracker should not be constructed for UPS")
            ut = UnifiedTracker()
            with self.assertRaises(NotImplementedError):
                ut.track("1Z999AA10123456784", carrier="ups")


if __name__ == "__main__":
    unittest.main()
