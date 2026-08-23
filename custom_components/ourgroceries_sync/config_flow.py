"""Config flow for OurGroceries Sync."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from ourgroceries import OurGroceries
from ourgroceries.exceptions import InvalidLoginException

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _build_schema(defaults: dict) -> vol.Schema:
    """Schema for the login step — email + password."""
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(
                CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


async def _test_login(username: str, password: str) -> str:
    """Try logging into OurGroceries.

    Returns "ok" or "invalid_auth". Any other failure (network, OurGroceries
    down, unexpected response shape) is treated as "cannot_connect" rather
    than crashing the flow.
    """
    try:
        og = OurGroceries(username, password)
        await og.login()
        return "ok"
    except InvalidLoginException:
        return "invalid_auth"
    except Exception:  # noqa: BLE001
        return "cannot_connect"


class OurGroceriesSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Step 1 — email and password."""
        errors = {}

        if user_input is not None:
            result = await _test_login(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if result == "ok":
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
            errors["base"] = result

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict):
        """Handle reauthentication triggered by expired/invalid credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict | None = None):
        """Ask for updated credentials for the existing entry and verify them."""
        errors = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            result = await _test_login(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if result == "ok":
                return self.async_update_reload_and_abort(entry, data=user_input)
            errors["base"] = result

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_build_schema(user_input or entry.data),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict | None = None):
        """Let the user change their stored credentials at any time.

        Same form/validation as setup and reauth, just user-initiated
        (Settings -> Devices & Services -> this integration -> Configure)
        instead of triggered by a login failure.
        """
        errors = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            result = await _test_login(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if result == "ok":
                return self.async_update_reload_and_abort(entry, data=user_input)
            errors["base"] = result

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(user_input or entry.data),
            errors=errors,
        )
