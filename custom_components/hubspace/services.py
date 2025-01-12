import asyncio
import logging

from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import verify_domain_control

from .bridge import HubspaceBridge
from .const import DOMAIN

SERVICE_SEND_COMMAND = "send_command"

LOGGER = logging.getLogger(__name__)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Hubspace integration."""

    async def send_command(call: ServiceCall, skip_reload=True) -> None:
        states: list[dict] = []
        states.append(
            {
                "value": call.data.get("value"),
                "functionClass": call.data.get("functionClass"),
                "functionInstance": call.data.get("functionInstance"),
            }
        )
        entity_reg = er.async_get(hass)
        tasks = []
        account = call.data.get("account")
        for entity_name in call.data.get("entity_id", []):
            entity = entity_reg.async_get(entity_name)
            if not entity:
                LOGGER.warning("Entity %s not found", entity_name)
                return
            bridge = await find_bridge(hass, account)
            if bridge:
                tasks.append(bridge.api.send_service_request(entity.unique_id, states))
            else:
                LOGGER.warning("No bridge using account %s", account)
                return
        await asyncio.gather(*tasks)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_COMMAND,
            verify_domain_control(hass, DOMAIN)(send_command),
        )


async def find_bridge(hass: HomeAssistant, username: str) -> HubspaceBridge | None:
    """Find the bridge for the given username"""
    for bridge in hass.data[DOMAIN].values():
        if username is None:
            return bridge
        if bridge.config_entry.data[CONF_USERNAME] == username:
            return bridge
    return None
