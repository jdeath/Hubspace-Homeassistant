"""Config flow for HubSpace integration."""

from __future__ import annotations

import logging
from asyncio import timeout
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from hubspace_async import HubSpaceConnection

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

LOGIN_REQS = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
}
LOGIN_SCHEMA = vol.Schema(LOGIN_REQS)


class HubSpaceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HubSpace"""

    VERSION = 1
    username: str
    password: str
    conn: HubSpaceConnection

    async def perform_auth(
        self, step_id: str, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Validate and save auth"""

        errors = {}
        if not user_input:
            return self.async_show_form(
                step_id=step_id,
                data_schema=LOGIN_SCHEMA,
                errors=errors,
            )
        else:
            try:
                async with timeout(10):
                    self.conn = HubSpaceConnection(
                        user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                    )
                    await self.conn.get_account_id()
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["unknown"] = "generic"
            else:
                await self.async_set_unique_id(
                    await self.conn.account_id, raise_on_progress=False
                )
                # self._abort_if_unique_id_configured()
                return self.async_create_entry(title=DOMAIN, data=user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return await self.perform_auth("user", user_input)
