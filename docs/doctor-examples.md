# `tday doctor` examples (JSON)

This doc shows copy/paste examples and sample (redacted) JSON payloads for support tickets and CI.

## Notes

- `--json` prints **valid JSON to stdout** and suppresses human/colored output.
- Secrets are never printed. Sensitive fields show only presence/length.
- UPS/USPS network checks are **not implemented yet** (config validation only).

---

## FedEx: config + OAuth + optional track

```bash
tday doctor --carrier fedex --env prod --tracking-number 395579987149 --json | jq
```

Key fields to look at:
- `.config.valid` (bool)
- `.network.oauth.ok` (bool)
- `.network.track.ok` (bool)

---

## UPS/USPS: config validation (stubbed)

```bash
tday doctor --carrier ups --env prod --json | jq
tday doctor --carrier usps --env prod --json | jq
```

Expected today:
- `.network.implemented == false`
- `.network.note == "network checks not implemented for this carrier"`

---

## Carrier auto-detection

```bash
tday doctor --carrier auto --tracking-number 1Z999AA10123456784 --json | jq
```

Look at:
- `.carrier.detected`
- `.carrier.effective`

---

## Aggregate all carriers: `doctor --all`

`--all` runs the doctor flow for **fedex + ups + usps** and emits one aggregated JSON object.

```bash
tday doctor --all --env prod --json | jq
```

Example (shape only; values redacted/truncated):

```json
{
  "doctor_version": 1,
  "mode": "all",
  "env": "prod",
  "tracking_number": "395579987149",
  "carriers": {
    "fedex": { "doctor_version": 1, "carrier": { "effective": "fedex" }, "config": { "valid": true }, "network": { "oauth": { "ok": true } } },
    "ups":   { "doctor_version": 1, "carrier": { "effective": "ups" },   "config": { "valid": false }, "network": { "implemented": false } },
    "usps":  { "doctor_version": 1, "carrier": { "effective": "usps" },  "config": { "valid": false }, "network": { "implemented": false } }
  },
  "summary": {
    "rc": 2,
    "by_carrier": { "fedex": 0, "ups": 2, "usps": 2 },
    "config_valid": { "fedex": true, "ups": false, "usps": false }
  }
}
```

### Exit code behavior in `--all` mode

Overall exit code is the most severe across carriers:
- `4` if any carrier reports a track failure (FedEx only today)
- `3` if any carrier reports an OAuth failure (FedEx only today)
- `2` if any carrier has missing/invalid config
- `0` only if all carriers are OK

