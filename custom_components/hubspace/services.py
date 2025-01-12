import asyncio
import logging
from typing import Final

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import verify_domain_control

from .bridge import HubspaceBridge
from .const import DOMAIN

SERVICE_SEND_COMMAND = "send_command"

SERVICE_SEND_COMMAND_FUNC_CLASS: Final[str] = "functionClass"
SERVICE_SEND_COMMAND_FUNC_INSTANCE: Final[str] = "functionInstance"
SERVICE_SEND_COMMAND_VALUE: Final[str] = "value"
SERVICE_SEND_COMMAND_ACCOUNT: Final[str] = "account"

LOGGER = logging.getLogger(__name__)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Hubspace integration."""

    async def send_command(call: ServiceCall, skip_reload=True) -> None:
        states: list[dict] = []
        states.append(
            {
                "value": call.data.get(SERVICE_SEND_COMMAND_VALUE),
                "functionClass": call.data.get(SERVICE_SEND_COMMAND_FUNC_CLASS),
                "functionInstance": call.data.get(SERVICE_SEND_COMMAND_FUNC_INSTANCE),
            }
        )
        entity_reg = er.async_get(hass)
        tasks = []
        account = call.data.get("account")
        for entity_name in call.data.get("entity_id", []):
            entity = entity_reg.async_get(entity_name)
            bridge = await find_bridge(hass, account)
            if bridge:
                tasks.append(bridge.api.send_service_request(entity.unique_id, states))
            else:
                LOGGER.warning("No bridge using account %s", account)
                return
        await asyncio.gather(*tasks)

    def optional(value):
        if value is None:
            return value
        return cv.string(value)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_COMMAND,
            verify_domain_control(hass, DOMAIN)(send_command),
            schema=vol.Schema(
                {
                    vol.Required("entity_id"): cv.entity_ids,
                    vol.Required(SERVICE_SEND_COMMAND_FUNC_CLASS): cv.string,
                    vol.Required(SERVICE_SEND_COMMAND_VALUE): cv.string,
                    vol.Optional(SERVICE_SEND_COMMAND_FUNC_INSTANCE): optional,
                    vol.Optional(SERVICE_SEND_COMMAND_ACCOUNT): optional,
                }
            ),
        )


async def find_bridge(hass: HomeAssistant, username: str) -> HubspaceBridge | None:
    """Find the bridge for the given username"""
    for bridge in hass.data[DOMAIN].values():
        if username is None:
            return bridge
        if bridge.config_entry.data[CONF_USERNAME] == username:
            return bridge
    return None
