"""Config flow for HubSpace integration."""

from __future__ import annotations

import contextlib
import logging
from asyncio import timeout
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from hubspace_async import HubSpaceConnection, InvalidAuth, InvalidResponse

from .const import DEFAULT_TIMEOUT, DOMAIN
from .const import VERSION_MAJOR as const_maj
from .const import VERSION_MINOR as const_min

_LOGGER = logging.getLogger(__name__)

LOGIN_REQS = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
}
OPTIONAL = {
    vol.Required(CONF_TIMEOUT): int,
}
LOGIN_SCHEMA = vol.Schema(LOGIN_REQS | OPTIONAL)
RECONFIG_SCHEMA = vol.Schema(OPTIONAL)


class HubSpaceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HubSpace"""

    VERSION = const_maj
    MINOR_VERSION = const_min
    username: str
    password: str
    conn: HubSpaceConnection

    async def validate_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> Optional[str]:
        """Validate and save auth"""
        err_type = None
        try:
            async with timeout(user_input[CONF_TIMEOUT] / 1000):
                self.conn = HubSpaceConnection(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                await self.conn.get_account_id()
        except TimeoutError:
            err_type = "cannot_connect"
        except (InvalidAuth, InvalidResponse):
            err_type = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            err_type = "unknown"
        return err_type

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_TIMEOUT] = user_input[CONF_TIMEOUT] or DEFAULT_TIMEOUT
            except ValueError:
                errors["base"] = "invalid_timeout"
            if not (err_type := await self.validate_auth(user_input)):
                await self.async_set_unique_id(
                    await self.conn.account_id, raise_on_progress=False
                )
                # self._abort_if_unique_id_configured()
                await self.conn.client.close()
                return self.async_create_entry(title=DOMAIN, data=user_input)
            else:
                errors["base"] = err_type
        with contextlib.suppress(Exception):
            await self.conn.client.close()
        return self.async_show_form(
            step_id="user",
            data_schema=LOGIN_SCHEMA,
            errors=errors,
        )
