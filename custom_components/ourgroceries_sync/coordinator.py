"""DataUpdateCoordinator for OurGroceries shopping-list sync."""
import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from ourgroceries import OurGroceries

from .const import DOMAIN, LIST_SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class OurGroceriesCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Poll OurGroceries shopping lists.

    Re-fetches a list's items only when its versionId has actually changed
    since the last poll — this is the fix OurGroceries' own developer asked
    for in home-assistant/core#105700, applied here to the shopping lists.
    The master list used for autocomplete suggestions is handled separately
    in services.py and is deliberately NOT part of this polling loop — it
    changes rarely, so an on-demand, longer-lived cache suits it better than
    a 60-second poll would.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, og: OurGroceries) -> None:
        """Initialize the coordinator."""
        self.og = og
        self.lists: list[dict] = []
        self._cache: dict[str, dict] = {}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=LIST_SCAN_INTERVAL_SECONDS),
        )

    async def _update_list(self, list_id: str, version_id: str) -> None:
        """Refetch a single list's items only if its versionId changed."""
        cached_version = self._cache.get(list_id, {}).get("list", {}).get("versionId", "")
        if cached_version == version_id:
            return
        self._cache[list_id] = await self.og.get_list_items(list_id=list_id)

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch the list of lists, then refresh any list whose contents changed."""
        self.lists = (await self.og.get_my_lists())["shoppingLists"]
        await asyncio.gather(*[self._update_list(sl["id"], sl["versionId"]) for sl in self.lists])
        return self._cache
