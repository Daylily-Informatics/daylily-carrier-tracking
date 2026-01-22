# daylily-carrier-tracking

Unified multi-carrier tracking library.

- **FedEx**: implemented (Track API v1 + optional Ship fallback)
- **UPS/USPS**: scaffolded (not implemented yet)

## Install (dev)

```bash
pip install -e .
```

## Configure FedEx credentials

By default it uses `yaml_config_day`.

Create:

```text
~/.config/fedex/fedex_prod.yaml
---
api_url: https://apis.fedex.com/oauth/token
client_id: ...
client_secret: ...
# optional overrides:
# track_url: https://apis.fedex.com/track/v1/trackingnumbers
# ship_track_url: https://apis.fedex.com/ship/v1/trackingnumbers
```

## CLI

```bash
tracking_day --help
tracking_day fedex <TRACKING_NUMBER> --api-preference auto|track|ship [--no-raw] [--pretty]
tracking_day track <TRACKING_NUMBER> --carrier auto|fedex|ups|usps [--no-raw] [--pretty]
```

## Tests

```bash
python -m unittest discover -s tests
```
