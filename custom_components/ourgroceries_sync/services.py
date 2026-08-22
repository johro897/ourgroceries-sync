"""Suggestions and category-lookup services for OurGroceries Sync.

No background polling for either of these, on purpose — unlike the todo.*
list sync in coordinator.py, which does need real polling since shopping
lists change often. OurGroceries' own developer filed
home-assistant/core#105700 against the official integration for hammering
their (unofficial, tolerated) API with unnecessary polling — the fix they
asked for was to only re-fetch when something actually changed. Both the
master list and the category names change rarely, so instead of polling
them on a timer, these services are called on-demand by a card and backed
by a simple time-based cache — OurGroceries' API gets hit at most once per
cache window, integration-wide, no matter how often the service is called.
"""
import logging
import time

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.helpers import entity_registry as er
from ourgroceries import OurGroceries

from .const import (
    CATEGORY_CACHE_SECONDS,
    DOMAIN,
    SERVICE_GET_CATEGORIES,
    SERVICE_GET_SUGGESTIONS,
    SUGGESTIONS_CACHE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the get_suggestions and get_categories services."""

    # {entry_id: (fetched_at_monotonic, [{"name": ..., "note": ...}, ...])}
    suggestions_cache: dict[str, tuple[float, list[dict]]] = {}
    # {entry_id: (fetched_at_monotonic, {category_id: category_name})}
    category_cache: dict[str, tuple[float, dict[str, str]]] = {}

    def _get_coordinator():
        """Return the (entry_id, coordinator) for whichever entry is loaded.

        This integration only supports one OurGroceries account in
        practice, so there's no config_entry selector to keep these
        services simple to call.
        """
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            return None, None
        return next(iter(entries.items()))

    async def _category_names(entry_id: str, og: OurGroceries) -> dict[str, str]:
        """Return {category_id: category_name}, cached for CATEGORY_CACHE_SECONDS."""
        cached = category_cache.get(entry_id)
        if cached is not None:
            fetched_at, names = cached
            if time.monotonic() - fetched_at < CATEGORY_CACHE_SECONDS:
                return names

        _LOGGER.debug("ourgroceries_sync: fetching category list from OurGroceries")
        data = await og.get_category_items()
        raw_items = data.get("list", {}).get("items", [])
        names = {item["id"]: item["name"] for item in raw_items if item.get("id") and item.get("name")}

        category_cache[entry_id] = (time.monotonic(), names)
        return names

    async def get_suggestions(call: ServiceCall) -> ServiceResponse:
        """Return known item names (with notes) from the OurGroceries master list."""
        entry_id, coordinator = _get_coordinator()
        if coordinator is None:
            return {"items": []}
        og = coordinator.og

        cached = suggestions_cache.get(entry_id)
        if cached is not None:
            fetched_at, items = cached
            if time.monotonic() - fetched_at < SUGGESTIONS_CACHE_SECONDS:
                _LOGGER.debug("ourgroceries_sync: returning cached suggestions")
                return {"items": items}

        _LOGGER.debug("ourgroceries_sync: fetching master list from OurGroceries")
        data = await og.get_master_list()
        raw_items = data.get("list", {}).get("items", [])

        # A name can appear more than once in principle — last one wins.
        # The master list is meant to hold unique known item names, so this
        # is a safety net, not an expected case.
        by_name: dict[str, str | None] = {}
        for item in raw_items:
            name = item.get("name")
            if not name:
                continue
            by_name[name] = item.get("note") or None

        items = [{"name": name, "note": note} for name, note in sorted(by_name.items())]

        suggestions_cache[entry_id] = (time.monotonic(), items)
        return {"items": items}

    async def get_categories(call: ServiceCall) -> ServiceResponse:
        """Return {item_uid: category_name} for the targeted todo.* entity's list.

        Entity-targeted like todo.get_items, but registered as a plain
        domain service (not an entity-platform service) since it isn't
        backed by an HA entity of its own — so the response isn't keyed by
        entity_id the way an entity-service response would be; the caller
        only ever targets one entity_id at a time anyway.
        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        if isinstance(entity_id, list):
            entity_id = entity_id[0] if entity_id else None
        if not entity_id:
            return {"categories": {}}

        entry_id, coordinator = _get_coordinator()
        if coordinator is None:
            return {"categories": {}}

        registry_entry = er.async_get(hass).async_get(entity_id)
        list_id = registry_entry.unique_id if registry_entry else None
        if not list_id:
            return {"categories": {}}

        list_data = coordinator.data.get(list_id)
        if not list_data:
            return {"categories": {}}

        names = await _category_names(entry_id, coordinator.og)
        items = list_data.get("list", {}).get("items", [])
        categories = {
            item["id"]: names.get(item["categoryId"], "")
            for item in items
            if item.get("id") and item.get("categoryId")
        }
        return {"categories": categories}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SUGGESTIONS,
        get_suggestions,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_CATEGORIES,
        get_categories,
        supports_response=SupportsResponse.ONLY,
    )
