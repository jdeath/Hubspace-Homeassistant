"""Hubspace integration."""

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry
from hubspace_async import HubSpaceConnection

from .const import UPDATE_INTERVAL_OBSERVATION
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


@dataclass
class HubSpaceData:
    """Data for HubSpace integration."""

    coordinator_hubspace: HubSpaceDataUpdateCoordinator


type HubSpaceConfigEntry = ConfigEntry[HubSpaceData]


async def async_setup_entry(hass: HomeAssistant, entry: HubSpaceData) -> bool:
    """Set up HubSpace as config entry."""
    websession = async_get_clientsession(hass)
    conn = HubSpaceConnection(
        entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], websession=websession
    )

    coordinator_hubspace = HubSpaceDataUpdateCoordinator(
        hass,
        conn,
        [],
        [],
        UPDATE_INTERVAL_OBSERVATION,
    )

    await coordinator_hubspace.async_config_entry_first_refresh()

    entry.runtime_data = HubSpaceData(
        coordinator_hubspace=coordinator_hubspace,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: HubSpaceConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device.

    A device can only be removed if it is not present in the current API response
    """
    device_id = list(device_entry.identifiers)[0][1]
    return not any(
        [
            x
            for x in config_entry.runtime_data.coordinator_hubspace.tracked_devices
            if x.device_id == device_id
        ]
    )
