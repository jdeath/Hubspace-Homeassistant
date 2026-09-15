"""Config flow for Hubspace integration."""

from __future__ import annotations

from asyncio import timeout
from collections.abc import Mapping
import logging
from typing import Any

from aioafero import InvalidAuth, InvalidOTP, OTPRequired
from aioafero.v1 import AferoAuth
from aioafero.v1.auth import TokenData
from aioafero.v1.v1_const import AFERO_CLIENTS
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import BooleanSelector
import voluptuous as vol

from .const import (
    CONF_CLIENT,
    CONF_ENABLE_CONCLAVE,
    CONF_OTP,
    CONF_REFRESH_TOKEN,
    DEFAULT_CLIENT,
    DEFAULT_ENABLE_CONCLAVE,
    DEFAULT_POLLING_INTERVAL_SEC,
    DEFAULT_TIMEOUT,
    DOMAIN,
    POLLING_TIME_STR,
    VERSION_MAJOR as const_maj,
    VERSION_MINOR as const_min,
)

_LOGGER = logging.getLogger(__name__)

LOGIN_REQS = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_CLIENT): vol.In(sorted(AFERO_CLIENTS.keys())),
}
OTP_REQS = {
    vol.Required(CONF_OTP): str,
}
REAUTH_REQS = {
    vol.Required(CONF_PASSWORD): str,
}
OPTIONAL = {
    vol.Required(CONF_TIMEOUT): int,
    vol.Required(POLLING_TIME_STR): int,
    # BooleanSelector always submits true/false (plain bool can omit when unchecked).
    vol.Required(
        CONF_ENABLE_CONCLAVE, default=DEFAULT_ENABLE_CONCLAVE
    ): BooleanSelector(),
}
LOGIN_SCHEMA = vol.Schema(LOGIN_REQS | OPTIONAL)
RECONFIG_SCHEMA = vol.Schema(OPTIONAL)


class AferoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Afero."""

    VERSION = const_maj
    MINOR_VERSION = const_min

    def __init__(self) -> None:
        """Initialize."""
        self._auth: AferoAuth | None = None
        self._token_data: TokenData | None = None
        self._otp_code: str | None = None
        self._username: str | None = None
        self._password: str | None = None
        self._polling: int | None = DEFAULT_POLLING_INTERVAL_SEC
        self._timeout: int | None = DEFAULT_TIMEOUT
        self._enable_conclave: bool = DEFAULT_ENABLE_CONCLAVE
        self._client: str | None = None

    async def _async_afero_login(
        self, step_id: str, schema: vol.Schema
    ) -> ConfigFlowResult:
        """Validate the Afero username and password."""
        errors = {}
        session = aiohttp_client.async_get_clientsession(self.hass)
        self._auth = AferoAuth.for_login(
            session,
            self._username,
            self._password,
            afero_client=self._client,
            client_name="Home Assistant",
        )
        try:
            async with timeout(self._timeout):
                self._token_data = await self._auth.login()
        except TimeoutError:
            errors = {"base": "cannot_connect"}
        except InvalidAuth:
            errors = {"base": "invalid_auth"}
        except OTPRequired:
            return await self.async_step_otp()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors = {"base": "unknown"}
        if errors:
            return self.async_show_form(
                step_id=step_id, data_schema=schema, errors=errors
            )
        return await self._async_create_entry()

    async def _async_afero_otp(self) -> ConfigFlowResult:
        """Handle the OTP step for Afero."""
        try:
            async with timeout(self._timeout):
                self._token_data = await self._auth.submit_otp(self._otp_code)
        except InvalidOTP:
            return self.async_show_form(
                step_id="otp",
                data_schema=vol.Schema(OTP_REQS),
                errors={"base": "invalid_otp"},
            )
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return self.async_show_form(
                step_id="otp",
                data_schema=vol.Schema(OTP_REQS),
                errors={"base": "unknown_otp"},
            )
        return await self._async_create_entry()

    async def _async_create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        unique_id = self._username.lower()
        existing_entry = await self.async_set_unique_id(unique_id)
        data = {
            CONF_USERNAME: self._username,
            CONF_CLIENT: self._client,
            CONF_REFRESH_TOKEN: self._token_data.refresh_token,
        }
        options = {
            CONF_TIMEOUT: self._timeout or DEFAULT_TIMEOUT,
            POLLING_TIME_STR: self._polling or DEFAULT_POLLING_INTERVAL_SEC,
            CONF_ENABLE_CONCLAVE: self._enable_conclave,
        }
        # Password is only used for the login handshake; never persist it.
        self._password = None
        if existing_entry:
            return self.async_update_reload_and_abort(
                existing_entry, data=data, options=options
            )
        return self.async_create_entry(
            title=unique_id,
            data=data,
            options=options,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=LOGIN_SCHEMA,
            )
        try:
            user_input.update(validate_options(user_input))
        except ValueError as err:
            return self.async_show_form(
                step_id="user",
                data_schema=LOGIN_SCHEMA,
                errors={"base": str(err)},
            )
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._client = user_input[CONF_CLIENT]
        self._timeout = user_input[CONF_TIMEOUT]
        self._polling = user_input[POLLING_TIME_STR]
        self._enable_conclave = user_input.get(
            CONF_ENABLE_CONCLAVE, DEFAULT_ENABLE_CONCLAVE
        )
        return await self._async_afero_login("user", LOGIN_SCHEMA)

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle an OTP flow."""
        if user_input is None:
            return self.async_show_form(step_id="otp", data_schema=vol.Schema(OTP_REQS))
        self._otp_code = user_input[CONF_OTP]
        return await self._async_afero_otp()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization request from Afero."""
        current = self._get_reauth_entry()
        self._username = current.data[CONF_USERNAME]
        self._password = None
        # reauth workflow is used as part of the migration and CONF_CLIENT may not be set
        self._client = current.data.get(CONF_CLIENT, DEFAULT_CLIENT)
        self._timeout = current.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self._polling = current.options.get(
            POLLING_TIME_STR, DEFAULT_POLLING_INTERVAL_SEC
        )
        self._enable_conclave = current.options.get(
            CONF_ENABLE_CONCLAVE, DEFAULT_ENABLE_CONCLAVE
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization flow."""
        reauth_schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): str,
            }
        )
        if not user_input:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=reauth_schema,
            )
        self._password = user_input[CONF_PASSWORD]
        return await self._async_afero_login("reauth_confirm", reauth_schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AferoOptionsFlowHandler:
        """Get the options flow for this handler."""
        return AferoOptionsFlowHandler()


class AferoOptionsFlowHandler(OptionsFlow):
    """Handle options config flow for Afero."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle UI Options workflow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input.update(validate_options(user_input))
            except ValueError as err:
                errors["base"] = str(err)
            if not errors:
                return self.async_create_entry(data=user_input)
            errors["base"] = "polling_too_short"
        poll_time = self.config_entry.options.get(
            POLLING_TIME_STR, DEFAULT_POLLING_INTERVAL_SEC
        )
        tmout = self.config_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        enable_conclave = self.config_entry.options.get(
            CONF_ENABLE_CONCLAVE, DEFAULT_ENABLE_CONCLAVE
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TIMEOUT, default=tmout): int,
                    vol.Optional(POLLING_TIME_STR, default=poll_time): int,
                    vol.Required(
                        CONF_ENABLE_CONCLAVE, default=enable_conclave
                    ): BooleanSelector(),
                },
            ),
            errors=errors,
        )


def validate_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate optional settings shared by setup and the options flow."""
    validated = {
        POLLING_TIME_STR: user_input.get(POLLING_TIME_STR, DEFAULT_POLLING_INTERVAL_SEC)
        or DEFAULT_POLLING_INTERVAL_SEC,
        CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT,
        # Default on (opt-out). Absent key = legacy entries / tests without the field.
        CONF_ENABLE_CONCLAVE: user_input.get(
            CONF_ENABLE_CONCLAVE, DEFAULT_ENABLE_CONCLAVE
        ),
    }
    if validated[POLLING_TIME_STR] < 2:
        raise ValueError("polling_too_short")
    return validated
