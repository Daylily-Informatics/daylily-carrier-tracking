# daylily-carrier-tracking

Unified multi-carrier tracking library.

- **FedEx**: implemented (Track API v1 + optional Ship fallback)
- **UPS/USPS**: scaffolded (not implemented yet)

## Install (dev)

```bash
pip install -e .
```

## Configure FedEx credentials

Create:

```text
~/.config/daylily-carrier-tracking/fedex_prod.yaml
---
oauth_url: https://apis.fedex.com/oauth/token
client_id: ...
client_secret: ...
# optional overrides:
# track_url: https://apis.fedex.com/track/v1/trackingnumbers
# ship_track_url: https://apis.fedex.com/ship/v1/trackingnumbers
```

Notes:
- The library/CLI will **prefer** `~/.config/daylily-carrier-tracking/<carrier>_<env>.yaml`.
- For backward compatibility, if that file is missing it will fall back to `yaml_config_day`'s legacy location `~/.config/<carrier>/<carrier>_<env>.yaml`.

## CLI

```bash
tday --help
tday fedex <TRACKING_NUMBER> --api-preference auto|track|ship [--no-raw] [--pretty]
tday track <TRACKING_NUMBER> --carrier auto|fedex|ups|usps [--no-raw] [--pretty]

# deprecated alias:
tracking_day --help
```

## Tests

```bash
python -m unittest discover -s tests
```
