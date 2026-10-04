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

Changed your OurGroceries password (or want to switch accounts)? **Settings → Devices & Services → OurGroceries Sync → Configure** — no need to remove and re-add the integration.

If you're upgrading from **HA core's built-in OurGroceries integration**, you can remove it after setting this one up — its `todo.*` entities will need to be re-bound in any dashboards/automations that reference them, since the entity IDs will differ. If you're upgrading from the earlier **OurGroceries Autocomplete** (this project's previous, suggestions-only incarnation), see "Upgrading" below.

## Usage

### Shopping lists

Once configured, each OurGroceries list appears as a `todo.*` entity, usable with Home Assistant's standard todo card, voice assistants, and the `todo.*` services — same as any other todo integration. If an item has a note in OurGroceries (e.g. "125g"), it's exposed as that item's standard `description` field — read-only, since the underlying API only supports setting a note when an item is created, not editing one on an existing item (see "Adding an item with a note" below for the create-time path).

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

### Adding an item with a note

`todo.add_item` (the standard HA service) has no way to set a note — that would need this integration to declare `SET_DESCRIPTION_ON_ITEM`, which would also make HA offer description *editing* via `todo.update_item`, and there's no way to actually honor an edit to an existing item's note (the underlying API only supports setting one at creation). So note-on-create is its own service instead:

```yaml
service: ourgroceries_sync.add_item
target:
  entity_id: todo.groceries
data:
  item: Oat milk
  note: 125g
```

`note` is optional — omit it for a plain add (equivalent to `todo.add_item`). Used by [ourgroceries-shopping-card](https://github.com/johro897/ourgroceries-shopping-card) when you click a suggestion that has a note attached.

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

## Troubleshooting

**Setup fails with an invalid-login error**
Double-check your OurGroceries email and password — this integration logs in independently of any other OurGroceries setup you may have (see "No relation to HA core's official integration" above), so credentials that work in the OurGroceries app or a different integration still need to be re-entered here.

**Integration shows as needing reauthentication**
OurGroceries rejected the stored credentials (e.g. after a password change). Follow the reauth prompt, or go to **Settings → Devices & Services → OurGroceries Sync → Configure** to update credentials any time, not just after a failure.

**No shopping list entities after setup**
Restart Home Assistant once after adding the integration. If lists still don't appear, confirm you're logged into the same OurGroceries account that owns the lists you expect to see.

**Suggestions are missing an item you just added in OurGroceries, or a category name is out of date**
Both are cached for 15 minutes integration-wide, by design (see "Why the master list isn't kept live-synced" above) — wait for the cache to expire, or restart Home Assistant to force a refresh immediately.

**A note isn't attached when an item is added via automation/template**
`todo.add_item` (the standard HA service) has no note field — use `ourgroceries_sync.add_item` with a `note` field instead, see "Adding an item with a note" above.

## Changelog

### 1.2.1 — Align with ourgroceries 1.6.0 (pre-release `beta-1.2.1`)

- The `ourgroceries` library requirement changed from the exact pin `1.5.4` to a minimum version, `>=1.6.0`, so it follows Home Assistant core (HA 2026.10 moved to `1.6.0`). The new library version only adds a bulk-edit method, so nothing this integration uses changed. Fixes the failing Hassfest check ([#6](https://github.com/johro897/ourgroceries-sync/issues/6)).
- Checking off or unchecking an item now sends one request to OurGroceries instead of two: the no-op rename that used to precede every status change is skipped unless the name actually changed.
- Declared the integration config-entry-only, which clears a Hassfest warning. No behaviour change.

### 1.2.0 — First stable release

Renamed from **OurGroceries Autocomplete** (suggestions-only) to a full replacement for HA core's built-in `ourgroceries` integration. Went through several pre-release betas (`beta-1.0.0` through `beta-1.1.4`, still published on the [releases page](https://github.com/johro897/ourgroceries-sync/releases) as history) before this first stable release:

- `todo.*` entity per shopping list — create, update, delete, with delete concurrency bounded to stay under OurGroceries' rate limit (see [home-assistant/core#179603](https://github.com/home-assistant/core/issues/179603))
- Reauthentication triggers correctly on invalid/expired credentials, plus a **Configure** option to update credentials any time, not just on failure
- `get_suggestions` — item names and notes from your OurGroceries master list, 15-minute cache, no background polling
- `get_categories` — category name per item on a list, for category-grouped card UIs
- `add_item` — create an item with a note attached, since `todo.add_item` has no note field; validated against the wrong kind of entity fails cleanly rather than crashing
- Item notes exposed via the standard `description` field
- English and Swedish translations throughout

## License

MIT License — see [LICENSE](LICENSE)
