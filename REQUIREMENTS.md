# REQUIREMENTS — daylily-carrier-tracking

Implementation contract for the unified multi-carrier tracking library + CLI.

## Goals
- One Python package: `daylily_carrier_tracking`
- One CLI entrypoint: `tracking_day`
- Input: a single tracking number (+ optional explicit carrier)
- Output: **normalized ops-meta** (stable schema) + optional **raw** carrier payload

FedEx is implemented. UPS + USPS are scaffolded and are the next implementations.

## Non-goals (for now)
- No persistence layer (DB/cache service).
- No bulk tracking (single tracking number per call/CLI invocation).
- No attempt to fully normalize event/scan history across carriers (raw keeps fidelity).
- No paid aggregator integrations unless explicitly added later.

## Compatibility / constraints
- Python: **3.10+**
- Keep deps minimal: stdlib + existing deps (`requests`, `yaml_config_day`).
- Tests must not do real network calls (mock `requests`).
- Carrier auth/access patterns will change; isolate auth + HTTP per-carrier to minimize blast radius.

## Public API requirements
All carriers must return the same shape from `.track(...)`:

- `carrier`: `"fedex" | "ups" | "usps"`
- `tracking_number`: `str`
- `source`: `dict`
  - `api`: string identifier (ex: `"fedex.track.v1"`)
  - `endpoint`: URL used
  - `timestamp_utc`: ISO-8601 UTC timestamp
- `ops_meta`: dict (mandatory keys below; always present)
- `raw`: optional carrier response JSON (present when `include_raw=True`)

### ops-meta schema (mandatory)
`ops_meta` must always include these keys (even when unknown):
- `Pickup_dt`
- `Delivery_dt`
- `Tender_dt`
- `Ship_dt`
- `Transit_Time_sec`
- `Delivery_Status`
- `Origin_state`
- `Destination_state`
- `Destination_city`
- `Origin_city`
- `Delivery_weekday`
- `Ship_weekday`
- `Origin_state_alt`
- `Destination_state_alt`

Defaults / missing conventions:
- Use `default_ops_meta()` as the baseline.
- Unknown string: `"na"` or empty string (match existing FedEx behavior).
- Unknown numeric: `-1`.

### Error handling contract
- NOTFOUND / invalid tracking number: must **not crash**.
  - Return default ops-meta.
  - Include enough detail in `raw` (when available) to debug.
- Unimplemented carriers: library raises `NotImplementedError`; CLI exits **2**.
- Auth/network errors: raise an informative exception in library (preferred); CLI prints to stderr + non-zero exit.

## CLI requirements
Single console script: `tracking_day`.

Global flags:
- `--pretty`: pretty-print JSON.

Subcommands (current contract):
- `tracking_day fedex <TN> [--api-preference auto|track|ship] [--no-raw]`
- `tracking_day track <TN> [--carrier auto|fedex|ups|usps] [--no-raw]`
- `tracking_day ups <TN> [--no-raw]` (until implemented: exit 2)
- `tracking_day usps <TN> [--no-raw]` (until implemented: exit 2)

Output:
- JSON to stdout.
- Errors to stderr.

## Configuration & secrets
### Primary mechanism: yaml_config_day
Trackers should load credentials via `yaml_config_day` when `config` is not provided.

FedEx current config keys (required/used by implementation):
- `client_id`
- `client_secret`
- `oauth_url` **or** `api_url` (either name accepted)
Optional overrides:
- `track_url`
- `ship_track_url`

File convention:
- `~/.config/<proj>/<proj>_<env>.yaml` (example: `~/.config/fedex/fedex_prod.yaml`)

### Override mechanism: `config: dict`
All trackers must accept `config: dict | None` so callers/tests can bypass `yaml_config_day`.

## Carrier-specific implementation requirements

### FedEx (implemented)
Must continue to support:
- OAuth2 client-credentials
- Token caching + proactive refresh
- Track API v1 + optional Ship fallback
- `api_preference`: `auto | track | ship` with `auto` doing Track then Ship on NOTFOUND (if configured)

### UPS (to implement)
Create `daylily_carrier_tracking/ups_tracker.py` with an `UpsTracker` analogous to `FedexTracker`.

Requirements:
- OAuth2 client-credentials
- Cached token with expiry; refresh before expiry
- Tracking endpoint + version captured in `source.api`
- Normalization best-effort into ops-meta

Deliverables:
- UPS routing in `UnifiedTracker`
- CLI parity (`ups` subcommand + `track --carrier ups`)
- Unit tests (mocked HTTP): happy path, NOTFOUND defaults, token refresh path

### USPS (to implement)
Create `daylily_carrier_tracking/usps_tracker.py` with a `UspsTracker` analogous to `FedexTracker`.

Auth decision is variable (legacy Web Tools vs newer APIs). Requirements regardless:
- Isolate auth mechanism behind a provider object
- Normalize best-effort into ops-meta
- Tests (mocked HTTP): happy path, NOTFOUND defaults, auth failure

## Internal architecture requirements
- Keep each carrier in its own module:
  - token provider (if applicable)
  - request builder + HTTP wrapper
  - response normalizer
- Centralize per-carrier NOTFOUND detection in one function.
- Python 3.10 datetime parsing must handle trailing `Z` (convert to `+00:00` before `fromisoformat`).

## Testing
- `unittest` + `unittest.mock`
- No real network calls
- Run: `python -m unittest discover -s tests`

## Definition of Done (per carrier)
- `UnifiedTracker.track(..., carrier="<carrier>")` works under mocked tests
- CLI prints valid JSON with the normalized shape
- NOTFOUND returns defaults (no crash)
- Token refresh is covered by tests (where applicable)
