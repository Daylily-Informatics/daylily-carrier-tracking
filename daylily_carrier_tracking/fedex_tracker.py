import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import requests
from yaml import YAMLError

from .config import config_path, load_yaml_mapping


class FedexConfigurationError(ValueError):
    """A caller must configure the provider before a request can be made."""


class FedexLookupError(RuntimeError):
    """A failed provider operation, with an operator-safe message."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def _endpoint(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = urlsplit(value)
            if parsed.scheme in {"https", "http"} and parsed.hostname:
                return value
        except ValueError:
            pass
    raise FedexConfigurationError("The selected FedEx endpoint requires an absolute HTTP URL.")


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    # Python 3.10 datetime.fromisoformat() does not accept trailing 'Z'
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _weekday_name(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dt.weekday()]


def _get_nested(d: Dict[str, Any], path: Tuple[str, ...], default: Any = "") -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _default_ops_meta() -> Dict[str, Any]:
    return {
        "Carrier": "",
        "Pickup_dt": "",
        "Delivery_dt": "",
        "Tender_dt": "",
        "Ship_dt": "",
        # Match README invalid/expired example.
        "Transit_Time_sec": -1,
        "Delivery_Status": "na",
        "Origin_state": "na",
        "Destination_state": "na",
        "Destination_city": "",
        "Origin_city": "",
        "Delivery_weekday": "",
        "Ship_weekday": "",
        "Origin_state_alt": "",
        "Destination_state_alt": "",
    }


def default_ops_meta() -> Dict[str, Any]:
    """Public helper exposing the legacy ops-meta schema defaults."""
    return _default_ops_meta()


def normalize_fedex_track_ops_meta(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the legacy 'ops-meta' fields from a FedEx Track API v1 response.

    This is intentionally conservative and returns "na"/empty values when the
    payload is missing or indicates NOTFOUND.
    """

    ops = _default_ops_meta()
    ops["Carrier"] = "fedex"

    track_results = _get_nested(raw, ("output", "completeTrackResults"), default=[])
    if not track_results:
        return ops

    trk_res_list = track_results[0].get("trackResults") or []
    if not trk_res_list:
        return ops

    trk_res = trk_res_list[0]  # match README behavior: single summarized record
    if isinstance(trk_res, dict) and trk_res.get("error"):
        return ops

    # For a valid payload (no per-tracking error), keep Transit_Time_sec empty
    # unless we can compute it from dates.
    ops["Transit_Time_sec"] = ""

    ops["Origin_state"] = _get_nested(
        trk_res,
        ("originLocation", "locationContactAndAddress", "address", "stateOrProvinceCode"),
        default=ops["Origin_state"],
    )
    ops["Origin_city"] = _get_nested(
        trk_res,
        ("originLocation", "locationContactAndAddress", "address", "city"),
        default=ops["Origin_city"],
    )
    ops["Origin_state_alt"] = ops["Origin_state"]

    ops["Destination_state"] = _get_nested(
        trk_res,
        ("lastUpdatedDestinationAddress", "stateOrProvinceCode"),
        default=ops["Destination_state"],
    )
    ops["Destination_city"] = _get_nested(
        trk_res,
        ("lastUpdatedDestinationAddress", "city"),
        default=ops["Destination_city"],
    )
    ops["Destination_state_alt"] = _get_nested(
        trk_res,
        ("serviceDetail", "shortDescription"),
        default=ops["Destination_state_alt"],
    )

    status = _get_nested(trk_res, ("latestStatusDetail", "statusByLocale"), default="")
    if status:
        ops["Delivery_Status"] = status

    date_and_times = trk_res.get("dateAndTimes") or []
    for st in date_and_times:
        if not isinstance(st, dict):
            continue
        t = st.get("type")
        v = st.get("dateTime")
        if not t or not v:
            continue
        if "ACTUAL_PICKUP" in t:
            ops["Pickup_dt"] = v
        elif "ACTUAL_DELIVERY" in t:
            ops["Delivery_dt"] = v
        elif t == "SHIP" or "SHIP" in t:
            ops["Ship_dt"] = v
        elif "ACTUAL_TENDER" in t:
            ops["Tender_dt"] = v

    delivery_dt = _parse_iso_datetime(ops["Delivery_dt"])
    ship_dt = _parse_iso_datetime(ops["Ship_dt"])
    tender_dt = _parse_iso_datetime(ops["Tender_dt"])

    ops["Delivery_weekday"] = _weekday_name(delivery_dt)
    ops["Ship_weekday"] = _weekday_name(ship_dt)

    transit = ""
    start_dt = tender_dt or ship_dt
    if start_dt and delivery_dt and (start_dt.tzinfo is None) == (delivery_dt.tzinfo is None):
        transit = (delivery_dt - start_dt).total_seconds()
    ops["Transit_Time_sec"] = transit

    return ops


def _provider_error(errors: Any) -> FedexLookupError:
    if not isinstance(errors, list):
        errors = [errors]
    for error in errors:
        if isinstance(error, dict):
            code = str(error.get("code", "")).upper()
            if "TRACKING" in code and "NOTFOUND" in code.replace(".", ""):
                return FedexLookupError("not_found", "FedEx could not find this tracking number.")
    return FedexLookupError("provider_error", "FedEx reported an error during the lookup.")


def _require_tracking_result(raw: Dict[str, Any], requested_number: str) -> None:
    if raw.get("errors"):
        raise _provider_error(raw["errors"])
    groups = _get_nested(raw, ("output", "completeTrackResults"), default=None)
    if isinstance(groups, list) and len(groups) == 1 and isinstance(groups[0], dict):
        records = groups[0].get("trackResults")
        if isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict) and records[0]:
            record = records[0]
            if record.get("error"):
                raise _provider_error(record["error"])
            returned_numbers = (groups[0].get("trackingNumber"),
                                _get_nested(record, ("trackingNumberInfo", "trackingNumber"), None))
            if any(value is not None and value != requested_number for value in returned_numbers):
                raise FedexLookupError("invalid_response", "FedEx returned details for a different tracking number.")
            return
    raise FedexLookupError("invalid_response", "FedEx did not return a single tracking result.")


def _post(url: str, *, oauth: bool = False, **kwargs: Any) -> tuple[dict, int]:
    try:
        response = requests.post(url, **kwargs)
    except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema, requests.exceptions.InvalidURL):
        raise FedexConfigurationError("The selected FedEx endpoint URL is invalid.") from None
    except requests.Timeout:
        raise FedexLookupError("provider_timeout", "The FedEx request timed out.") from None
    except requests.RequestException:
        raise FedexLookupError("provider_unreachable", "The FedEx service could not be reached.") from None
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code in (401, 403) or (oauth and response.status_code == 400):
            raise FedexLookupError("authentication_failed", "FedEx rejected the configured credentials or access.") from None
        try:
            error_body = response.json()
        except ValueError:
            error_body = {}
        errors = error_body.get("errors") if isinstance(error_body, dict) else None
        raise _provider_error(errors) from None
    try:
        data = response.json()
    except ValueError:
        raise FedexLookupError("invalid_response", "FedEx returned unreadable JSON.") from None
    if not isinstance(data, dict):
        raise FedexLookupError("invalid_response", "FedEx returned an unexpected response format.")
    return data, response.status_code


@dataclass
class FedexApiCallMeta:
    api: str
    url: str
    http_status: Optional[int]
    elapsed_ms: Optional[int]


class FedexOAuthTokenProvider:
    def __init__(self, oauth_url: str, client_id: str, client_secret: str):
        self._oauth_url = oauth_url
        self._client_id = client_id
        self._client_secret = client_secret

        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    def get_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and self._expires_at and now < self._expires_at:
            return self._token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data, _ = _post(self._oauth_url, oauth=True, data=payload, headers=headers)
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise FedexLookupError("authentication_failed", "FedEx did not issue an OAuth access token.")
        try:
            expires_in = int(data.get("expires_in", 3300))
            expires_at = now + timedelta(seconds=max(0, expires_in - 60))
        except (TypeError, ValueError, OverflowError):
            raise FedexLookupError("invalid_response", "FedEx returned an invalid OAuth token lifetime.") from None

        # Refresh a bit early.
        self._token = token
        self._expires_at = expires_at
        return token


class FedexTracker:
    """Direct FedEx client. Each lookup uses the caller's selected endpoint."""

    def __init__(
        self,
        config_proj_name: str = "fedex",
        config_proj_env: str = "prod",
        config: Optional[Dict[str, Any]] = None,
        track_url: Optional[str] = None,
        ship_track_url: Optional[str] = None,
    ):
        if config is None:
            try:
                cfg = load_yaml_mapping(config_path(config_proj_name, config_proj_env))
            except (OSError, YAMLError, ValueError):
                raise FedexConfigurationError("The FedEx configuration could not be loaded.") from None
        else:
            if not isinstance(config, dict):
                raise FedexConfigurationError("The FedEx configuration must be a mapping.")
            cfg = config

        oauth_url = cfg.get("oauth_url") or cfg.get("api_url")
        if cfg.get("oauth_url") and cfg.get("api_url") and cfg["oauth_url"] != cfg["api_url"]:
            raise FedexConfigurationError("The FedEx configuration specifies conflicting OAuth endpoints.")
        if any(not isinstance(x, str) or not x.strip() for x in (oauth_url, cfg.get("client_id"), cfg.get("client_secret"))):
            raise FedexConfigurationError("FedEx requires an OAuth URL, client ID and client secret.")

        self._track_url = cfg.get("track_url") or track_url
        self._ship_track_url = cfg.get("ship_track_url") or ship_track_url

        self._token_provider = FedexOAuthTokenProvider(
            oauth_url=_endpoint(oauth_url),
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
        )

    def _post_json(self, url: str, payload: Dict[str, Any], api_name: str) -> Tuple[Dict[str, Any], FedexApiCallMeta]:
        token = self._token_provider.get_token()
        headers = {
            "Content-Type": "application/json",
            "X-locale": "en_US",
            "Authorization": "Bearer " + token,
        }
        started = time.time()
        data, http_status = _post(url, json=payload, headers=headers)
        elapsed_ms = int((time.time() - started) * 1000)
        return data, FedexApiCallMeta(api=api_name, url=url, http_status=http_status, elapsed_ms=elapsed_ms)

    def auth_token(self) -> str:
        return self._token_provider.get_token()

    def track_raw(self, tracking_number: str, api_preference: str = "track") -> Tuple[Dict[str, Any], FedexApiCallMeta]:
        """Return the raw JSON from the selected endpoint, including FedEx application errors."""
        payload = {
            "includeDetailedScans": True,
            "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": str(tracking_number)}}],
        }

        if api_preference not in {"track", "ship"}:
            raise ValueError("api_preference must be 'track' or 'ship'")
        url = self._track_url if api_preference == "track" else self._ship_track_url
        if not isinstance(url, str) or not url.strip():
            raise FedexConfigurationError("The selected FedEx tracking endpoint is not configured.")
        return self._post_json(_endpoint(url), payload, api_name=api_preference + "_v1")

    def track_ops_meta(self, tracking_number: str, api_preference: str = "track") -> Dict[str, Any]:
        return self.track(tracking_number, api_preference=api_preference, include_raw=False)["ops_meta"]

    def track(self, tracking_number: str, api_preference: str = "track", include_raw: bool = True) -> Dict[str, Any]:
        raw, meta = self.track_raw(tracking_number, api_preference=api_preference)
        _require_tracking_result(raw, str(tracking_number))
        try:
            ops = normalize_fedex_track_ops_meta(raw)
        except (AttributeError, TypeError, ValueError, OverflowError):
            raise FedexLookupError("invalid_response", "FedEx returned an unreadable tracking result.") from None
        out = {
            "carrier": "fedex",
            "tracking_number": str(tracking_number),
            "source": {
                "api": meta.api,
                "url": meta.url,
                "http_status": meta.http_status,
                "elapsed_ms": meta.elapsed_ms,
            },
            "ops_meta": ops,
        }
        if include_raw:
            out["raw"] = raw
        return out
