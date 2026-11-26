# Daylily Carrier Tracking

Identify the carrier from a scanned tracking number or shipping barcode, then request live tracking if the selected carrier is FedEx. Recognition runs entirely on the local machine, including for numbers the library has never seen. It returns the original scan, a decision and the plausible carriers. A matching format identifies a carrier candidate. It cannot establish that a shipment exists.

## Install

Python 3.10 or later:

```sh
python -m pip install daylily-carrier-tracking==1.0.0
```

Upgrading from 0.5.1? The migration guide covers the replacement for `detect_carrier()`, the lookup result envelope, FedEx enablement and the CLI changes. [Migration guide](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/docs/migration-1.0.md)

## Recognize a scan

```sh
tday recognize 1Z5R89390357567127 --pretty
```

```json
{
  "scan": "1Z5R89390357567127",
  "status": "identified",
  "candidates": [
    {"carrier_id": "ups", "display_name": "UPS", "tracking_number": "1Z5R89390357567127"}
  ]
}
```

These examples can all be recognized offline. The UPS and FedEx inputs come from the bundled barcode catalog.

| Scan | What the application can do |
| --- | --- |
| `1Z5R89390357567127` | Preselect UPS. An operator can change the selection. |
| `RB123456785GB` | Offer the postal issuer as a candidate. This shared international postal format leaves the delivery carrier ambiguous. |
| `0000-NORTH-7` | Keep the exact text and leave the carrier unknown. |
| `32971514560102447849175802862014` | Retain the full FedEx ASTRA scan and use the embedded `784917580286` for a FedEx query. |

```python
from daylily_carrier_tracking import recognize_tracking_number

result = recognize_tracking_number("1Z5R89390357567127")
suggested = result.candidates[0] if result.status == "identified" else None
print(result.scan, suggested.carrier_id if suggested else "Unknown")
```

An ambiguous result can have a single candidate when the format is shared. Check `status` before preselecting. Candidates can include carriers without a live adapter. The bundled catalog includes UPS, FedEx, USPS, DHL, Canada Post, Amazon and regional carriers. The reference describes coverage, the treatment of routing fields and the full Python result contract. [Python reference](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/REQUIREMENTS.md) · [Upstream format catalog v2.0.0](https://github.com/jkeen/tracking_number_data/tree/v2.0.0)

## Look up the selected number

FedEx is the live provider in 1.0.0. In Python, pass the FedEx configuration explicitly, or set `fedex_enabled=True` to use a configured file. A default `UnifiedTracker()` leaves live access disabled. The CLI's `track` command opts in and uses the configured FedEx file when applicable.

```python
import os
from daylily_carrier_tracking import UnifiedTracker

tracker = UnifiedTracker(fedex_config={
    "oauth_url": "https://apis.fedex.com/oauth/token",
    "track_url": "https://apis.fedex.com/track/v1/trackingnumbers",
    "client_id": os.environ["FEDEX_CLIENT_ID"],
    "client_secret": os.environ["FEDEX_CLIENT_SECRET"],
})
# scanner_text and selected_carrier come from the calling application.
outcome = tracker.track(scanner_text, carrier=selected_carrier, include_raw=False)
if outcome["status"] == "succeeded":
    print(outcome["ops_meta"]["Delivery_Status"])
elif outcome["status"] == "failed":
    print(outcome["reason"], outcome["message"])
```

An explicit carrier selection takes precedence over recognition. Passing `carrier="auto"` requests automatic selection. An unrecognized or ambiguous scan, a disabled adapter or a carrier without live support yields `not_attempted`. When FedEx is contacted and the request fails, the result is `failed`. A receiving application can use that distinction to decide when to record a failure note. The application owns its records and persistence.

## CLI

| Command | Behavior |
| --- | --- |
| `tday recognize SCAN [--pretty]` | Print offline recognition JSON. All three recognition outcomes exit 0. |
| `tday track SCAN [--carrier ID] [--no-raw] [--pretty]` | Print lookup JSON. Exit 0 for success, 2 for a skipped lookup and 1 for a failed lookup. Quote the scan if it contains whitespace. |
| `tday configure fedex --env prod` | Write the FedEx config interactively and request an OAuth token to validate credentials. Use `--skip-validate` to write config without the request. |
| `tday doctor --tracking-number SCAN --no-network --json` | Show recognition, effective carrier and applicable configuration diagnostics locally. Omitting `--no-network` permits the FedEx OAuth or lookup operation. [Diagnostic examples and exit codes](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/docs/doctor-examples.md) |
| `tday completion bash` or `tday completion zsh` | Print the completion script for the installed CLI. |
| `tday test` | Invoke the repository's unit-test runner from a checkout containing the tests. |

Configure the default FedEx production profile with the wizard or inject the same keys from a secrets manager. The standard file is `fedex_prod.yaml` in the `daylily-carrier-tracking` directory below the user's home configuration directory (`.config`). The Track endpoint is selected by default. The optional `--api-preference ship` requires an explicitly configured `ship_track_url`. Each lookup uses one selected route. [FedEx developer portal](https://developer.fedex.com/api/en-us/home.html)

For development, run the repository's `dev-setup.sh` to install into its local virtual environment. The `tday` launcher and shell completions are available from the checkout. The maintained commands are `tday recognize`, `tday track` and `tday doctor`; consult `tday --help` for the full command list.
