"""OurGroceries Autocomplete — exposes master-list item suggestions for autocomplete."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from ourgroceries import OurGroceries

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .services import async_setup_services

PLATFORMS: list[str] = []


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register services once, regardless of how many entries exist."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OurGroceries Autocomplete from a config entry."""
    og = OurGroceries(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    await og.login()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = og
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
