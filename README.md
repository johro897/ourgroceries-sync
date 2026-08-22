# OurGroceries Sync

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/johro897/ourgroceries-sync.svg)](https://github.com/johro897/ourgroceries-sync/releases)

A Home Assistant integration for OurGroceries: syncs your shopping lists as `todo.*` entities, and exposes your "master list" (the item-history OurGroceries' own app uses for autocomplete) as a service, so a Lovelace card can suggest items you've typed before.

Pairs with [ourgroceries-shopping-card](https://github.com/johro897/ourgroceries-shopping-card), which reads/writes a `todo.*` entity via Home Assistant's standard `todo.*` services (so it works with any list source), and separately calls this integration's `get_suggestions` service to power its add-item autocomplete. The card degrades gracefully with no suggestions if this integration isn't installed.

## Why this exists

This integration **replaces** Home Assistant's built-in [OurGroceries integration](https://www.home-assistant.io/integrations/ourgroceries/) rather than sitting alongside it. The built-in integration syncs `todo.*` entities but never exposes the master list (item-history), so getting autocomplete suggestions required a second, separate integration and a second login — confusing for no good reason.

It's also a chance to fix a couple of things found while reading the built-in integration's source as a reference:

- **Unbounded concurrent deletes.** The built-in integration fires one request per item on bulk delete with no limit — a user with 550 done items sent 550 simultaneous requests in 3 seconds, which is exactly the kind of load OurGroceries' own developer has [asked Home Assistant integrations to avoid](https://github.com/home-assistant/core/issues/105700). OurGroceries now caps concurrent requests at 15/user and returns errors beyond that (see [home-assistant/core#179603](https://github.com/home-assistant/core/issues/179603), filed by OurGroceries' own developer, unaddressed at the time this was written). This integration bounds delete concurrency to stay well under that cap.
- **Reauthentication.** This integration prompts for updated credentials if OurGroceries rejects them, instead of failing silently.

## Installation

### Via HACS

1. HACS → ⋮ → Custom repositories → add `https://github.com/johro897/ourgroceries-sync`, category **Integration**
2. Search for **OurGroceries Sync** and install
3. Restart Home Assistant

### Manual

1. Copy `custom_components/ourgroceries_sync/` into your `config/custom_components/` folder
2. Restart Home Assistant

## Setup

**Settings → Devices & Services → Add Integration → OurGroceries Sync**, then enter your OurGroceries email and password. One `todo.*` entity is created per OurGroceries shopping list.

If you're upgrading from **HA core's built-in OurGroceries integration**, you can remove it after setting this one up — its `todo.*` entities will need to be re-bound in any dashboards/automations that reference them, since the entity IDs will differ. If you're upgrading from the earlier **OurGroceries Autocomplete** (this project's previous, suggestions-only incarnation), see "Upgrading" below.

## Usage

### Shopping lists

Once configured, each OurGroceries list appears as a `todo.*` entity, usable with Home Assistant's standard todo card, voice assistants, and the `todo.*` services — same as any other todo integration.

### Autocomplete suggestions

Exposes `ourgroceries_sync.get_suggestions`. Call it from a template, automation, or (typically) from [ourgroceries-shopping-card](https://github.com/johro897/ourgroceries-shopping-card) to get back item names (with an optional note, e.g. "125g", if OurGroceries has one on file) from your OurGroceries master list:

```yaml
service: ourgroceries_sync.get_suggestions
```

Returns:
```json
{ "items": [{ "name": "Bananas", "note": null }, { "name": "Oat milk", "note": "125g" }] }
```

### Category names

Exposes `ourgroceries_sync.get_categories`, targeted at one of this integration's own `todo.*` entities, returning the category name for each item currently on that list (used by the shopping card to group items):

```yaml
service: ourgroceries_sync.get_categories
target:
  entity_id: todo.groceries
```

Returns:
```json
{ "categories": { "<item uid>": "Dairy", "<item uid>": "Produce" } }
```

Category names come from your OurGroceries account's own categories, cached for 15 minutes for the same reason as suggestions (see below) — this integration doesn't invent or assign categories itself.

## Why the master list isn't kept live-synced

OurGroceries' own developer [filed a complaint against Home Assistant's built-in integration](https://github.com/home-assistant/core/issues/105700) in 2023 for causing "significant load on our servers" by polling too aggressively. The master list (used for autocomplete) is built to avoid that mistake entirely: there's no background polling coordinator for it. `get_suggestions` fetches from OurGroceries on demand and caches the result in memory for **15 minutes**, integration-wide — no matter how often the service is called (e.g. by multiple dashboard sessions), OurGroceries' API is hit at most once per 15-minute window. The master list changes rarely (it's your accumulated item history, not your active shopping list), so this staleness window is a non-issue in practice. Your shopping lists themselves (the `todo.*` entities) poll every 60 seconds, but only re-fetch a list's items if its contents actually changed since the last poll.

## Upgrading from OurGroceries Autocomplete

This project used to be suggestions-only (no shopping lists) under the name **OurGroceries Autocomplete**, domain `ourgroceries_autocomplete`. Since Home Assistant config entries are tied to their domain, there's no automatic migration path — and since the old integration had zero entities, nothing breaks by starting fresh:

1. Settings → Devices & Services → remove the old **OurGroceries Autocomplete** entry
2. HACS → remove the old `ourgroceries-autocomplete` custom repository (confirm `config/custom_components/ourgroceries_autocomplete/` is actually gone afterward)
3. HACS → add this repository as a custom repository, category **Integration**, install
4. Settings → Devices & Services → Add Integration → **OurGroceries Sync**, re-enter your OurGroceries credentials
5. If you also had HA core's built-in OurGroceries integration installed for your lists, you can now remove it — see "Setup" above

## Requirements

- Home Assistant 2024.8 or newer (uses the `config_entry`-based `DataUpdateCoordinator` API)
- An OurGroceries account

## Changelog

### 1.1.0
- `get_suggestions` now returns each item's `note` alongside its name (e.g. "125g"), not just names — used by the shopping card to show subtext under suggestions
- New `ourgroceries_sync.get_categories` service, entity-targeted at one of this integration's `todo.*` entities, returning a category name per item — used by the shopping card to group the list view by category

### 1.0.0
- Renamed from OurGroceries Autocomplete — now a full replacement for HA core's built-in OurGroceries integration, not just a companion to it
- `todo.*` entity per shopping list: create, update, and delete items, with delete concurrency bounded to stay under OurGroceries' rate limit (see home-assistant/core#179603)
- Reauthentication flow now actually triggers on invalid/expired credentials
- `get_suggestions` service unchanged: item names from your OurGroceries master list, with a 15-minute cache to keep API usage polite
- English and Swedish translations for the config flow

## License

MIT License — see [LICENSE](LICENSE)
