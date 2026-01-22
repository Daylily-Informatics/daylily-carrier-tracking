import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from daylily_carrier_tracking.fedex_tracker import FedexTracker
from daylily_carrier_tracking.unified_tracker import UnifiedTracker


def _print_json(obj: Dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(obj, indent=2, sort_keys=True))
    else:
        print(json.dumps(obj))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tracking_day", description="Multi-carrier tracking (FedEx implemented; UPS/USPS pending)")
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    fedex = sub.add_parser("fedex", help="Track a FedEx tracking number")
    fedex.add_argument("tracking_number")
    fedex.add_argument("--api-preference", default="auto", choices=["auto", "track", "ship"], help="Route to track/ship endpoint")
    fedex.add_argument("--no-raw", action="store_true", help="Omit raw response")

    track = sub.add_parser("track", help="Track with carrier routing")
    track.add_argument("tracking_number")
    track.add_argument("--carrier", default="auto", choices=["auto", "fedex", "ups", "usps"], help="Carrier selection")
    track.add_argument("--no-raw", action="store_true", help="Omit raw response")

    ups = sub.add_parser("ups", help="Track a UPS tracking number (not implemented)")
    ups.add_argument("tracking_number")
    ups.add_argument("--no-raw", action="store_true", help="Omit raw response")

    usps = sub.add_parser("usps", help="Track a USPS tracking number (not implemented)")
    usps.add_argument("tracking_number")
    usps.add_argument("--no-raw", action="store_true", help="Omit raw response")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.cmd == "fedex":
            ft = FedexTracker()
            out = ft.track(args.tracking_number, api_preference=args.api_preference, include_raw=(not args.no_raw))
            _print_json(out, pretty=args.pretty)
            return 0

        if args.cmd == "track":
            ut = UnifiedTracker()
            out = ut.track(args.tracking_number, carrier=args.carrier, include_raw=(not args.no_raw))
            _print_json(out, pretty=args.pretty)
            return 0

        if args.cmd in {"ups", "usps"}:
            ut = UnifiedTracker()
            out = ut.track(args.tracking_number, carrier=args.cmd, include_raw=(not args.no_raw))
            _print_json(out, pretty=args.pretty)
            return 0

        raise ValueError("Unhandled command")
    except NotImplementedError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
