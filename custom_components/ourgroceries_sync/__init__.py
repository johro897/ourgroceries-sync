"""OurGroceries Sync — full todo.* list sync plus master-list autocomplete suggestions."""
from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from ourgroceries import OurGroceries
from ourgroceries.exceptions import InvalidLoginException

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import OurGroceriesCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.TODO]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register services once, regardless of how many entries exist."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OurGroceries Sync from a config entry."""
    og = OurGroceries(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        await og.login()
    except InvalidLoginException as err:
        # Triggers config_flow.py's async_step_reauth.
        raise ConfigEntryAuthFailed("OurGroceries rejected the stored credentials") from err
    except (TimeoutError, ClientError) as err:
        raise ConfigEntryNotReady("Could not reach OurGroceries") from err

    coordinator = OurGroceriesCoordinator(hass, entry, og)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
