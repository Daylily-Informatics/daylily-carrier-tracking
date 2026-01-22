import re
from typing import Any, Dict, Optional

from daylily_carrier_tracking.fedex_tracker import FedexTracker, default_ops_meta


def detect_carrier(tracking_number: str) -> str:
    """Best-effort carrier guess.

    This is intentionally conservative; ambiguous numeric-only numbers exist.
    """
    tn = (tracking_number or "").strip().upper()
    if tn.startswith("1Z"):
        return "ups"
    if re.fullmatch(r"[0-9]{12}|[0-9]{15}|[0-9]{20,22}", tn):
        # Could be FedEx or USPS depending on the range/format; default to fedex.
        return "fedex"
    if re.fullmatch(r"[A-Z]{2}[0-9]{9}[A-Z]{2}", tn):
        return "usps"
    return "fedex"


class UnifiedTracker:
    """Carrier-agnostic tracker facade.

    For now:
      - fedex is implemented via FedexTracker
      - ups/usps raise NotImplementedError (needs API creds + endpoint wiring)
    """

    def __init__(
        self,
        fedex_config_proj_name: str = "fedex",
        fedex_config_proj_env: str = "prod",
        fedex_config: Optional[Dict[str, Any]] = None,
    ):
        self._fedex = FedexTracker(
            config_proj_name=fedex_config_proj_name,
            config_proj_env=fedex_config_proj_env,
            config=fedex_config,
        )

    def track(self, tracking_number: str, carrier: str = "auto", include_raw: bool = True) -> Dict[str, Any]:
        carrier = (carrier or "auto").lower()
        if carrier == "auto":
            carrier = detect_carrier(tracking_number)

        if carrier == "fedex":
            return self._fedex.track(tracking_number, include_raw=include_raw)
        if carrier in {"ups", "usps"}:
            raise NotImplementedError(
                f"Carrier '{carrier}' is not implemented yet. "
                "Next step: add carrier auth + tracking endpoint wiring and a normalizer."
            )
        raise ValueError("carrier must be one of: auto, fedex, ups, usps")

    def track_ops_meta(self, tracking_number: str, carrier: str = "auto") -> Dict[str, Any]:
        try:
            return self.track(tracking_number, carrier=carrier, include_raw=False)["ops_meta"]
        except NotImplementedError:
            return default_ops_meta()
