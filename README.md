# OurGroceries Autocomplete

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/johro897/ourgroceries-autocomplete.svg)](https://github.com/johro897/ourgroceries-autocomplete/releases)

A small Home Assistant integration that exposes your OurGroceries "master list" (the item-history OurGroceries' own app uses for autocomplete) as a service, so a Lovelace card can suggest items you've typed before.

Pairs with [ourgroceries-shopping-card](https://github.com/johro897/ourgroceries-shopping-card), which reads this integration's service to power its add-item autocomplete. Neither repo requires the other to install, but the card's autocomplete feature does nothing useful without this integration.

## Why this exists

Home Assistant's own built-in [OurGroceries integration](https://www.home-assistant.io/integrations/ourgroceries/) only exposes a `todo.*` entity per shopping list — it doesn't expose the master list. The underlying Python library both integrations are built on (`ourgroceries` on PyPI) already has `get_master_list()`; the built-in integration just never calls it. This integration fills that one gap and nothing else — it doesn't touch your shopping lists at all, that's what the official integration and its `todo.*` entities are for.

## Installation

### Via HACS

1. HACS → ⋮ → Custom repositories → add `https://github.com/johro897/ourgroceries-autocomplete`, category **Integration**
2. Search for **OurGroceries Autocomplete** and install
3. Restart Home Assistant

### Manual

1. Copy `custom_components/ourgroceries_autocomplete/` into your `config/custom_components/` folder
2. Restart Home Assistant

## Setup

**Settings → Devices & Services → Add Integration → OurGroceries Autocomplete**, then enter your OurGroceries email and password.

This is a **separate login from Home Assistant's own built-in OurGroceries integration** — there's no supported way to share credentials/session between two independent integrations, so you'll enter your OurGroceries password here even if you've already set up the official integration.

## Usage

Exposes one service: `ourgroceries_autocomplete.get_suggestions`. Call it from a template, automation, or (typically) from [ourgroceries-shopping-card](https://github.com/johro897/ourgroceries-shopping-card) to get back a list of item names from your OurGroceries master list:

```yaml
service: ourgroceries_autocomplete.get_suggestions
```

Returns:
```json
{ "items": ["Bananas", "Milk", "Oat milk", "..."] }
```

## Why the master list isn't kept live-synced

OurGroceries' own developer [filed a complaint against Home Assistant's built-in integration](https://github.com/home-assistant/core/issues/105700) in 2023 for causing "significant load on our servers" by polling too aggressively. This integration is built to avoid that mistake entirely for the master list: there's no background polling coordinator for it at all. `get_suggestions` fetches from OurGroceries on demand and caches the result in memory for **15 minutes**, integration-wide — no matter how often the service is called (e.g. by multiple dashboard sessions), OurGroceries' API is hit at most once per 15-minute window. The master list changes rarely (it's your accumulated item history, not your active shopping list), so this staleness window is a non-issue in practice.

## Requirements

- Home Assistant 2024.1 or newer
- An OurGroceries account

## Changelog

### v1.0.0
- Initial release
- `get_suggestions` service returning item names from your OurGroceries master list, with a 15-minute cache to keep API usage polite
- English and Swedish translations for the config flow

## License

MIT License — see [LICENSE](LICENSE)
