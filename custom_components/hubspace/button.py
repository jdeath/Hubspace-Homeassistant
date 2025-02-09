import json
import os
from enum import Enum

import aiofiles
from aiohubspace import anonymize_devices, get_hs_device
from aiohubspace.v1 import HubspaceBridgeV1
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN


class DebugButtonEnum(Enum):
    ANON = "anon"
    RAW = "raw"


class DebugButton(ButtonEntity):

    def __init__(self, bridge: HubspaceBridge, instance: DebugButtonEnum):
        self.bridge = bridge
        self.api: HubspaceBridgeV1 = bridge.api
        self.logger = bridge.logger.getChild("debug-button")
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, bridge.config_entry.data[CONF_USERNAME])},
        )
        self.instance = instance
        if self.instance == DebugButtonEnum.ANON:
            self._attr_name = "Generate Debug"
            self._attr_unique_id = f"{bridge.config_entry.data[CONF_USERNAME]}-debug"
        elif self.instance == DebugButtonEnum.RAW:
            self._attr_name = "Generate Raw"
            self._attr_unique_id = f"{bridge.config_entry.data[CONF_USERNAME]}-raw"

    async def async_press(self) -> None:
        """Handle the button press."""
        data = await self.bridge.api.fetch_data()
        curr_directory = os.path.dirname(os.path.realpath(__file__))
        if self.instance == DebugButtonEnum.ANON:
            dev_dump = os.path.join(curr_directory, "_dump_hs_devices.json")
            self.logger.debug("Writing out anonymized device data to %s", dev_dump)
            devs = [get_hs_device(dev) for dev in data]
            async with aiofiles.open(dev_dump, "w") as fh:
                await fh.write(json.dumps(anonymize_devices(devs), indent=4))
        elif self.instance == DebugButtonEnum.RAW:
            data_dump = os.path.join(curr_directory, "_dump_raw.json")
            self.logger.debug("Writing out raw data to %s", data_dump)
            async with aiofiles.open(data_dump, "w") as fh:
                await fh.write(json.dumps(data, indent=4))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            DebugButton(bridge, DebugButtonEnum.ANON),
            DebugButton(bridge, DebugButtonEnum.RAW),
        ]
    )
