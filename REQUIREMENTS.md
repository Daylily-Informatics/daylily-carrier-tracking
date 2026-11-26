# Daylily Carrier Tracking 1.0 — Python API

Install `daylily-carrier-tracking==1.0.0` and import from `daylily_carrier_tracking`. Python 3.10 or later is supported. [Quickstart](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/README.md) · [Migration from 0.5.1](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/docs/migration-1.0.md)

## Offline recognition

```python
recognize_tracking_number(scan: str) -> RecognitionResult
```

The function evaluates the complete barcode against a packaged format catalog and applies the check-digit rules defined for matching formats. It takes a string, including a scanned full label or hand-entered tracking number. It makes no network request and needs no configuration. Passing a non-string raises `TypeError`.

| Public type | Fields |
| --- | --- |
| `RecognitionResult` | `scan: str` preserves the original input. `status` is `identified`, `ambiguous` or `unknown`. `candidates` is a tuple of distinct `CarrierCandidate` objects sorted by carrier ID. |
| `CarrierCandidate` | `carrier_id: str` is the machine identifier. `display_name: str` is the operator label. `tracking_number` is the query string for that carrier, or `None` when it cannot be determined. |

Both types are frozen dataclasses. Use `dataclasses.asdict(result)` and `json.dumps(...)` for a JSON representation; a tuple becomes a JSON array. Store the original `scan` when exact preservation matters. Queries for recognized formats can use uppercase characters, omit presentation whitespace and scanner headers, or contain an extracted field from the full label. Treat tracking numbers as strings throughout.

- **Identified** means exactly one carrier has identifying format evidence. A receiving form may preselect it and allow override.
- **Ambiguous** means more than one carrier is plausible, or the evidence comes only from a nonexclusive format. A global postal S10 code can suggest the issuing postal operator. A GS1 SSCC can suggest a container-label format. Neither establishes the delivery carrier. A bare 14-digit DHL format match alone is also ambiguous.
- **Unknown** means there is no supported match. Empty or unrecognized strings return an empty candidate tuple and preserve their original value.

### Catalog and query numbers

The distribution bundles the courier definitions and MIT license from [tracking_number_data v2.0.0](https://github.com/jkeen/tracking_number_data/tree/v2.0.0). They are loaded locally. Coverage includes Amazon, Canada Post, Canpar, DHL, DPD, FedEx, GOFO, Landmark Global, LaserShip, Old Dominion, OnTrac, Purolator, Spee-Dee, UPS, USPS, Yodel and YunExpress, plus international S10 postal labels. S10 issuer hints can use a country-specific postal ID. A catalog match describes a format; it does not confirm shipment or delivery.

The matcher can extract the FedEx query number from ASTRA and supported long Ground/Express labels, remove supported USPS routing ZIP fields, and extract the parcel number from a DPD 28-character label. For example, FedEx ASTRA label `32971514560102447849175802862014` yields query number `784917580286`. Leading zeros within an identifier remain significant. Matching operates on a working copy, with Code 128/GS1-128 `]C0` and `]C1` scanner prefixes and ASCII presentation spacing recognized. Unknown input remains available verbatim.

## Unified lookup

```python
UnifiedTracker(fedex_config_proj_name="fedex", fedex_config_proj_env="prod",
               fedex_config=None, *, fedex_enabled=None)
tracker.track(scan, carrier="auto", include_raw=True, *, api_preference="track")
tracker.track_ops_meta(scan, carrier="auto", *, api_preference="track")
```

A default instance has live access disabled. Passing a configuration mapping enables FedEx; an explicit `fedex_enabled=False` overrides that choice. To opt into the configured project/environment file, pass `fedex_enabled=True`. The profile is loaded lazily when a FedEx lookup is applicable.

Use `carrier="auto"` for an identified candidate, `carrier="unknown"` to retain an unknown selection, or pass a carrier ID to honor an operator’s choice. For a recognized label the selected carrier's decoded query number is used when available. A manual FedEx choice on an otherwise unknown scan can use the supplied tracking number. Caller input errors such as a non-string scan, invalid carrier argument or unsupported endpoint selection are programming errors.

| Outcome | Contents and interpretation |
| --- | --- |
| `succeeded` | FedEx returned a usable single-package result. `carrier`, `tracking_number`, `message` and `reason=None` accompany `ops_meta`, `source` and optionally `raw`. |
| `not_attempted` | The library skipped the lookup. Reasons are `carrier_unknown`, `carrier_ambiguous`, `lookup_unsupported`, `lookup_disabled`, `configuration_error`, `empty_tracking_number` and `query_number_unavailable`. |
| `failed` | A provider operation failed. Reasons are `authentication_failed`, `not_found`, `provider_error`, `provider_timeout`, `provider_unreachable` and `invalid_response`. The message is suitable for an operator-facing note. |

Each outcome carries `status`, `reason`, `message`, `carrier` and `tracking_number`. The carrier can be `None` for unresolved input. A skipped lookup or failure has no shipment observations. `track_ops_meta()` returns the same outcome envelope and omits the raw carrier payload. A consumer that allows receiving to continue after a provider failure can persist its Package independently and record a note from the failed outcome.

### Successful FedEx observations

`source` identifies the selected API, URL, HTTP status and elapsed milliseconds. With `include_raw=True`, `raw` contains the original FedEx response, including scan events when supplied. `ops_meta` uses the package’s existing field names:

| Group | Keys |
| --- | --- |
| Carrier and status | `Carrier`, `Delivery_Status` |
| Times | `Pickup_dt`, `Delivery_dt`, `Tender_dt`, `Ship_dt`, `Transit_Time_sec`, `Delivery_weekday`, `Ship_weekday` |
| Locations and legacy fields | `Origin_state`, `Origin_city`, `Destination_state`, `Destination_city`, `Origin_state_alt`, `Destination_state_alt` |

Missing legacy metadata fields can contain empty strings, `na` or a numeric sentinel. Determine lookup success from the outcome status.

### Direct FedEx interfaces

- `FedexTracker(config=...)` accepts the explicit configuration used by existing integrations. It also accepts the existing project/environment constructor parameters. Either `oauth_url` or `api_url` names the OAuth endpoint; supplying both with conflicting values is a configuration error. Provide `client_id`, `client_secret` and the tracking endpoint for the chosen route. `api_preference="track"` uses `track_url`; explicit `"ship"` uses `ship_track_url`.
- `auth_token()` obtains a token. `track_raw(number, api_preference="track")` returns the response mapping and request metadata; a successful HTTP response can contain a carrier-level error. `track()` interprets carrier errors and returns FedEx data on success. The direct `track_ops_meta()` returns only normalized metadata on success.
- Direct callers can catch `FedexConfigurationError` or `FedexLookupError`; the latter exposes a stable `reason`. `UnifiedTracker` translates these into the outcomes above.
- `default_ops_meta()` constructs the legacy blank metadata mapping. `normalize_fedex_track_ops_meta(raw)` remains available for callers that already own the FedEx transport. These helpers do not perform a lookup.
