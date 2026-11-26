"""Carrier selection and optional live lookup."""

from typing import Any

from .fedex_tracker import FedexConfigurationError, FedexLookupError, FedexTracker
from .recognition import recognize_tracking_number


class UnifiedTracker:
    """Look up a tracking number only when the selected provider is enabled."""

    def __init__(
        self,
        fedex_config_proj_name: str = "fedex",
        fedex_config_proj_env: str = "prod",
        fedex_config: dict[str, Any] | None = None,
        *,
        fedex_enabled: bool | None = None,
    ):
        self._fedex_config_proj_name = fedex_config_proj_name
        self._fedex_config_proj_env = fedex_config_proj_env
        self._fedex_config = fedex_config
        self._fedex_enabled = (fedex_config is not None) if fedex_enabled is None else fedex_enabled
        self._fedex: FedexTracker | None = None

    def _get_fedex(self) -> FedexTracker:
        if self._fedex is None:
            self._fedex = FedexTracker(
                config_proj_name=self._fedex_config_proj_name,
                config_proj_env=self._fedex_config_proj_env,
                config=self._fedex_config,
            )
        return self._fedex

    def track(
        self,
        scan: str,
        carrier: str = "auto",
        include_raw: bool = True,
        *,
        api_preference: str = "track",
    ) -> dict[str, Any]:
        """Resolve the carrier, then return a succeeded, skipped, or failed outcome.

        A manual selection can use a number from an unrecognized label. When
        the scan matches a selected carrier's label format, use its decoded
        query number. The caller retains the original scan in either case.
        """
        if not isinstance(scan, str):
            raise TypeError("scan must be a string")
        if not isinstance(carrier, str) or not carrier.strip():
            raise ValueError("carrier must be 'auto', 'unknown' or a carrier ID")
        selected = carrier.strip().lower()
        automatic = selected == "auto"
        query = scan

        def skipped(reason: str, message: str) -> dict[str, Any]:
            return {
                "status": "not_attempted",
                "carrier": selected if selected not in {"auto", "unknown"} else None,
                "tracking_number": query,
                "reason": reason,
                "message": message,
            }

        if not scan.strip():
            return skipped("empty_tracking_number", "No tracking number was supplied.")
        if selected == "unknown":
            return skipped("carrier_unknown", "The carrier is unknown.")

        recognition = recognize_tracking_number(scan)
        if automatic:
            if recognition.status == "unknown":
                return skipped("carrier_unknown", "The carrier could not be identified.")
            if recognition.status == "ambiguous":
                return skipped("carrier_ambiguous", "Select a carrier before requesting tracking.")
            selected = recognition.candidates[0].carrier_id

        candidate = next((match for match in recognition.candidates if match.carrier_id == selected), None)
        if candidate and candidate.tracking_number is not None:
            query = candidate.tracking_number
        if selected != "fedex":
            return skipped("lookup_unsupported", "Live lookup is unavailable for this carrier.")
        if not self._fedex_enabled:
            return skipped("lookup_disabled", "FedEx lookup is disabled.")
        if automatic and candidate and candidate.tracking_number is None:
            return skipped("query_number_unavailable", "The label does not identify a FedEx query number.")

        try:
            result = self._get_fedex().track(query, include_raw=include_raw, api_preference=api_preference)
        except FedexConfigurationError as exc:
            return skipped("configuration_error", str(exc))
        except FedexLookupError as exc:
            return {
                "status": "failed",
                "carrier": selected,
                "tracking_number": query,
                "reason": exc.reason,
                "message": str(exc),
            }
        return {**result, "status": "succeeded", "reason": None, "message": "FedEx tracking retrieved."}

    def track_ops_meta(self, scan: str, carrier: str = "auto", *, api_preference: str = "track") -> dict[str, Any]:
        """Return the lookup outcome and, when successful, normalized metadata."""
        return self.track(scan, carrier, include_raw=False, api_preference=api_preference)
