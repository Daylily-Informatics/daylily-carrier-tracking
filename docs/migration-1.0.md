# Migrate from 0.5.1 to 1.0.0

Install the release with `python -m pip install daylily-carrier-tracking==1.0.0`. Applications can adopt offline recognition while retaining their direct FedEx integration.

## Replace the single carrier guess

In 0.5.1, `detect_carrier(scan)` returned a string and defaulted unrecognized input to FedEx. Version 1.0.0 removes that function.

```python
# 0.5.1
from daylily_carrier_tracking import detect_carrier

carrier = detect_carrier(scan)
```

```python
# 1.0.0
from daylily_carrier_tracking import recognize_tracking_number

result = recognize_tracking_number(scan)
original_scan = result.scan
suggested = result.candidates[0] if result.status == "identified" else None
carrier_id = suggested.carrier_id if suggested else None
choices = [(c.carrier_id, c.display_name) for c in result.candidates]
```

An ambiguous result may contain one candidate for a shared format. Keep **Unknown** selected for ambiguous and unknown results, offer plausible choices, and let the operator enter or override the carrier. Preserve the original scan separately from the candidate's query number.

Try these inputs with `tday recognize SCAN --pretty`:

| Input | Recognition | Useful downstream value |
| --- | --- | --- |
| `1Z5R89390357567127` | Identified | UPS |
| `A0000000000` | Ambiguous | Both Amazon and UPS are plausible |
| `0000-NORTH-7` | Unknown | The full string, including all four leading zeros |
| `32971514560102447849175802862014` | Identified | FedEx tracking number `784917580286` |

## Migrate live tracking

```python
# 0.5.1 — metadata-only call
ops = UnifiedTracker().track_ops_meta(number)
```

```python
# 1.0.0 — explicitly configured, operator-selected FedEx
from daylily_carrier_tracking import UnifiedTracker

tracker = UnifiedTracker(fedex_config=fedex_settings)
outcome = tracker.track(number, carrier="fedex", include_raw=False)
if outcome["status"] == "succeeded":
    ops = outcome["ops_meta"]
elif outcome["status"] == "failed":
    failure_note = outcome["message"]
else:
    skip_reason = outcome["reason"]
```

- For an operator-selected carrier, pass its ID. For automatic selection, pass `"auto"`. For an explicitly unknown carrier, pass `"unknown"`. Only FedEx can produce live observations in this release.
- `UnifiedTracker()` leaves live lookup disabled. Enable it with a configuration mapping or `fedex_enabled=True` for the configured profile file. Set `track_url` explicitly. The default endpoint selection is `"track"`. To deliberately use another configured FedEx endpoint, pass `api_preference="ship"` and supply `ship_track_url`. Migrate any old `api_preference="auto"` callers.
- `UnifiedTracker.track_ops_meta()` returns an outcome envelope without the raw carrier response. Read `ops_meta` inside a successful outcome. A skipped lookup is distinct from a definitive provider failure; unsuccessful outcomes contain a reason and an operator-facing message.
- Migrate legacy configuration into the central Daylily carrier-tracking profile or supply the mapping directly. OAuth settings are `oauth_url` (or the existing `api_url` spelling), `client_id` and `client_secret`.
- Existing integrations can still import `FedexTracker`, `normalize_fedex_track_ops_meta` and `default_ops_meta`. The direct client raises `FedexLookupError` for unsuccessful interpreted results; `track_raw()` retains raw successful-HTTP responses, including FedEx application errors. A consumer with its own transport can use recognition without changing its network path.

## Migrate CLI consumers

| Previous use | Version 1.0.0 |
| --- | --- |
| Infer a carrier by invoking a live tracking command | Use `tday recognize SCAN --pretty`. Read `status` and `candidates` from stdout. Detection requires no credentials. |
| `tracking_day` or the `tday fedex`, `tday ups`, `tday usps` shorthand | Use `tday track SCAN --carrier ID` for an explicit request. |
| `tday track SCAN --api-preference auto` | Omit the option for Track, or request `--api-preference ship` explicitly. |
| Parse `track` metadata regardless of exit status | Read the JSON outcome. Exit 0 is succeeded, 2 is not attempted, and 1 is failed. |
| Read doctor report version 1 | Version 2 includes `recognition`, distinguishes the requested, detected and effective carrier, and reports the unified outcome for an attempted tracking lookup. |

[Python API](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/REQUIREMENTS.md) · [Doctor examples](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/docs/doctor-examples.md)
