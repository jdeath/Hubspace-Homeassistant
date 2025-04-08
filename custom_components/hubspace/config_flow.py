"""Config flow for Hubspace integration."""

from __future__ import annotations

import contextlib
import logging
from asyncio import timeout
from collections import namedtuple
from typing import Any, Optional

import voluptuous as vol
from aiohubspace import InvalidAuth
from aiohubspace.v1 import HubspaceBridgeV1
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    DEFAULT_POLLING_INTERVAL_SEC,
    DEFAULT_TIMEOUT,
    DOMAIN,
    POLLING_TIME_STR,
)
from .const import VERSION_MAJOR as const_maj
from .const import VERSION_MINOR as const_min

_LOGGER = logging.getLogger(__name__)

LOGIN_REQS = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
}
REAUTH = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)
OPTIONAL = {
    vol.Required(CONF_TIMEOUT): int,
    vol.Required(POLLING_TIME_STR): int,
}
LOGIN_SCHEMA = vol.Schema(LOGIN_REQS | OPTIONAL)
RECONFIG_SCHEMA = vol.Schema(OPTIONAL)


auth_result = namedtuple("auth_result", ["token", "err_type"])


class HubspaceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hubspace"""

    VERSION = const_maj
    MINOR_VERSION = const_min
    username: str
    password: str
    conn: HubspaceBridgeV1

    async def validate_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> Optional[auth_result]:
        """Validate and save auth"""
        err_type = None
        self.bridge = HubspaceBridgeV1(
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
        )
        try:
            async with timeout(user_input[CONF_TIMEOUT] / 1000):
                await self.bridge.get_account_id()
        except TimeoutError:
            err_type = "cannot_connect"
        except InvalidAuth:
            err_type = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            err_type = "unknown"
        finally:
            await self.bridge.close()
        return auth_result(self.bridge.refresh_token, err_type)

    @staticmethod
    def extract_user_data(user_input: dict[str, Any] | None) -> tuple[dict, dict]:
        options = {}
        data = {}
        importable_options = [CONF_TIMEOUT, POLLING_TIME_STR]
        for key in user_input:
            if key in importable_options:
                options[key] = user_input[key]
            else:
                data[key] = user_input[key]
        return data, options

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult | dict:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_TIMEOUT] = user_input.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT
            user_input[POLLING_TIME_STR] = user_input.get(POLLING_TIME_STR) or 30
            unique_id: str = user_input[CONF_USERNAME].lower()
            await self.async_set_unique_id(unique_id, raise_on_progress=False)
            data, options = self.extract_user_data(user_input)
            if (
                self.source == config_entries.SOURCE_REAUTH
                and self._get_reauth_entry().unique_id != self.unique_id
            ):
                errors["base"] = "unique_id_mismatch"
                return self.async_show_form(
                    step_id="user",
                    data_schema=LOGIN_SCHEMA,
                    errors=errors,
                )
            auth_data = await self.validate_auth(user_input)
            if not auth_data.err_type:
                data[CONF_TOKEN] = auth_data.token
                if user_input[POLLING_TIME_STR] < 2:
                    errors["base"] = "polling_too_short"
                else:
                    if self.source == config_entries.SOURCE_REAUTH:
                        return self.async_update_reload_and_abort(
                            self._get_reauth_entry(),
                            data_updates=data,
                            options=options,
                        )
                    else:
                        self._abort_if_unique_id_configured(reload_on_update=True)
                        return self.async_create_entry(
                            title=unique_id, data=data, options=options
                        )
            else:
                errors["base"] = auth_data.err_type
        with contextlib.suppress(Exception):
            await self.bridge.close()
        return self.async_show_form(
            step_id="user",
            data_schema=LOGIN_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a reauth flow"""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HubspaceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return HubspaceOptionsFlowHandler()


class HubspaceOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[POLLING_TIME_STR] == 0:
                user_input[POLLING_TIME_STR] = DEFAULT_POLLING_INTERVAL_SEC
            if user_input[POLLING_TIME_STR] < 2:
                errors["base"] = "polling_too_short"
            if not errors:
                return self.async_create_entry(data=user_input)
            errors["base"] = "polling_too_short"
        poll_time = self.config_entry.options.get(
            POLLING_TIME_STR, DEFAULT_POLLING_INTERVAL_SEC
        )
        tmout = self.config_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TIMEOUT, default=tmout): int,
                    vol.Optional(POLLING_TIME_STR, default=poll_time): int,
                },
            ),
            errors=errors,
        )
