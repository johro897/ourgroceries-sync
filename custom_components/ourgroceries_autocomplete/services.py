"""Services for OurGroceries Autocomplete.

No background polling here on purpose. OurGroceries' own developer filed
home-assistant/core#105700 against the official integration for hammering
their (unofficial, tolerated) API with unnecessary polling — the fix they
asked for was to only re-fetch when something actually changed. The master
list this integration reads changes rarely (it's a person's list of known
grocery items), so instead of polling it on a timer, this service is called
on-demand by a card and backed by a simple time-based cache — OurGroceries'
API gets hit at most once per SUGGESTIONS_CACHE_SECONDS, integration-wide,
no matter how often the service is called.
"""
import logging
import time

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback

from .const import DOMAIN, SERVICE_GET_SUGGESTIONS, SUGGESTIONS_CACHE_SECONDS

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the get_suggestions service."""

    # {entry_id: (fetched_at_monotonic, [item names])}
    cache: dict[str, tuple[float, list[str]]] = {}

    async def get_suggestions(call: ServiceCall) -> ServiceResponse:
        """Return known item names from the OurGroceries master list.

        Uses whichever configured entry is loaded — this integration only
        supports one OurGroceries account in practice, so there's no
        config_entry selector to keep the service simple to call.
        """
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            return {"items": []}

        entry_id, og = next(iter(entries.items()))

        cached = cache.get(entry_id)
        if cached is not None:
            fetched_at, items = cached
            if time.monotonic() - fetched_at < SUGGESTIONS_CACHE_SECONDS:
                _LOGGER.debug("ourgroceries_autocomplete: returning cached suggestions")
                return {"items": items}

        _LOGGER.debug("ourgroceries_autocomplete: fetching master list from OurGroceries")
        data = await og.get_master_list()
        raw_items = data.get("list", {}).get("items", [])
        items = sorted({item["name"] for item in raw_items if item.get("name")})

        cache[entry_id] = (time.monotonic(), items)
        return {"items": items}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SUGGESTIONS,
        get_suggestions,
        supports_response=SupportsResponse.ONLY,
    )
