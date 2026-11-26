# Diagnose carrier configuration with tday doctor

Use `tday recognize` when you only need to identify a barcode. Use `tday doctor` to inspect the carrier selection, configuration and, when requested, provider access. Add `--json` for the version 2 machine-readable report.

## Offline examples

```sh
tday recognize '0000-NORTH-7' --pretty
tday doctor --tracking-number '0000-NORTH-7' --no-network --json
tday doctor --tracking-number 'RB123456785GB' --no-network --json
tday doctor --carrier fedex --env prod --no-network --json
```

Both scans are valid inputs to the recognition command, which exits 0. For the unfamiliar scan, the doctor report contains `recognition.status="unknown"`. For the S10 postal scan the status is `ambiguous`. In both cases the detected and effective carrier are null, configuration is not loaded, and doctor exits 2 because it cannot select a provider to diagnose. The explicit FedEx example inspects the production profile locally. With `--no-network`, no OAuth or carrier request is made.

## FedEx OAuth and lookup

```sh
tday doctor --carrier fedex --env prod --json
tday doctor --carrier fedex --tracking-number "$TRACKING_NUMBER" --json
```

The first command requests an OAuth token using the selected configuration. The second performs a live FedEx lookup for the supplied number and includes the outcome at `network.track.response`. On success, `tracking.normalized` contains the FedEx metadata. On a failed tracking call the outcome includes the provider reason and operator-safe message. Use a tracking number for which you intend to make a live request.

With no carrier argument, a supplied tracking number selects automatic detection. With neither a carrier nor a tracking number the default diagnostic is FedEx. Use `--config-path` to specify a single profile explicitly.

## Read the report

| Key | Meaning |
| --- | --- |
| `doctor_version` | `2`. |
| `recognition` | Full offline result for the supplied scan, or null when there was no scan. |
| `carrier.requested`, `detected`, `effective` | The command's selection, the unique detected carrier if present, and the carrier actually chosen for diagnostics. |
| `config` | Configuration source, path, key presence and validity when examined. |
| `network` | Whether network operations were requested and implemented, and any results of OAuth or tracking. |
| `tracking` | Supplied number and normalized observations when the lookup succeeds. |

Explicit UPS/USPS diagnostics can inspect their existing configuration fields. Live lookup coverage in 1.0.0 is FedEx only. For an aggregate configuration report, use `tday doctor --all --no-network --json`. The aggregate includes per-carrier exit codes under `summary.by_carrier`. With a scan, it attaches that scan only to the uniquely matched carrier's diagnostic. A single `--config-path` is incompatible with `--all`.

| Doctor exit code | Meaning |
| --- | --- |
| 0 | The selected checks completed successfully. |
| 2 | Carrier unresolved, diagnostic unavailable, configuration incomplete or lookup skipped. |
| 3 | FedEx authentication failed. |
| 4 | FedEx tracking failed after selection. |

The aggregate returns the highest-priority exit code across its reports. For the separate `tday track` exit codes and migration notes, see the [CLI guide](https://github.com/Daylily-Informatics/daylily-carrier-tracking/blob/1.0.0/README.md#cli).
