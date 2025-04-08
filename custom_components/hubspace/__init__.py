"""Hubspace integration."""

import logging

from aiohubspace import InvalidAuth
from aiohubspace.v1 import HubspaceBridgeV1
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .bridge import HubspaceBridge
from .const import (
    DEFAULT_POLLING_INTERVAL_SEC,
    DEFAULT_TIMEOUT,
    DOMAIN,
    POLLING_TIME_STR,
)
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hubspace as config entry."""
    bridge = HubspaceBridge(hass, entry)
    if not await bridge.async_initialize_bridge():
        return False

    async_register_services(hass)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, bridge.config_entry.data[CONF_USERNAME]),
        },
        name=f"hubspace-{bridge.config_entry.data[CONF_USERNAME]}",
        manufacturer="Hubspace",
        model="Cloud API",
    )
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )
    res = True
    if config_entry.version == 1:
        await perform_v2_migration(hass, config_entry)
    if config_entry.version == 2 and config_entry.minor_version == 0:
        await perform_v3_migration(hass, config_entry)
    if config_entry.version == 3 and config_entry.minor_version == 0:
        res = await perform_v4_migration(hass, config_entry)
    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return res


async def perform_v2_migration(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Fixes for v2 migration

    * Ensure CONF_TIMEOUT is present in the data
    """
    new_data = {**config_entry.data}
    new_data[CONF_TIMEOUT] = DEFAULT_TIMEOUT
    hass.config_entries.async_update_entry(
        config_entry, data=new_data, version=2, minor_version=0
    )


async def perform_v3_migration(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Fixes for v3 migration

    * Ensure CONF_TIMEOUT is present in options and removed from data
    * Ensure POLLING_TIME_STR is set in options and removed from data (dev build)
    * Ensure unique_id is set to the account in lowercase
    * Ensure the title is set to the account in lowercase
    """
    options = {**config_entry.options}
    data = {**config_entry.data}
    options[POLLING_TIME_STR] = (
        data.pop(POLLING_TIME_STR, None)
        or options.get(POLLING_TIME_STR)
        or DEFAULT_POLLING_INTERVAL_SEC
    )
    options[CONF_TIMEOUT] = (
        data.pop(CONF_TIMEOUT, None) or options.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT
    )
    # Previous versions may have used None for the unique ID
    unique_id = config_entry.data[CONF_USERNAME].lower()
    hass.config_entries.async_update_entry(
        config_entry,
        data=data,
        options=options,
        version=3,
        minor_version=0,
        unique_id=unique_id,
        title=unique_id,
    )


async def perform_v4_migration(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Fixes for v4 migration

    * Ensure CONF_TOKEN is set
    """
    options = {**config_entry.options}
    data = {**config_entry.data}
    # Generate the new token
    api = HubspaceBridgeV1(
        config_entry.data[CONF_USERNAME],
        config_entry.data[CONF_PASSWORD],
        session=aiohttp_client.async_get_clientsession(hass),
        polling_interval=config_entry.options[POLLING_TIME_STR],
    )
    try:
        await api.get_account_id()
    except InvalidAuth:
        config_entry.async_start_reauth(hass)
        return False
    data[CONF_TOKEN] = api.refresh_token
    # Previous versions may have used None for the unique ID
    unique_id = config_entry.data[CONF_USERNAME].lower()
    hass.config_entries.async_update_entry(
        config_entry,
        data=data,
        options=options,
        version=4,
        minor_version=0,
        unique_id=unique_id,
        title=unique_id,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_success = await hass.data[DOMAIN][entry.entry_id].async_reset()
    if len(hass.data[DOMAIN]) == 0:
        hass.data.pop(DOMAIN)
    return unload_success
