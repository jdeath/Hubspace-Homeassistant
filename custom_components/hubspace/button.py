"""Home Assistant entity for interacting with Afero buttons."""

from enum import Enum
import json
import os
from pathlib import Path

from aioafero import EventType, anonymize_devices, get_afero_device
from aioafero.v1 import AferoBridgeV1
import aiofiles
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN


class DebugButtonEnum(Enum):
    """Enumeration for debug button types in the Hubspace integration.

    ANON: Generate anonymized data for debugging
    RAW: Generate raw data for debugging
    """

    ANON = "anon"
    RAW = "raw"


DEVICE_NAMES = {
    DebugButtonEnum.ANON: "Generate Debug",
    DebugButtonEnum.RAW: "Generate Raw",
}


class DebugButton(ButtonEntity):
    """Representation of an Afero Button."""

    def __init__(self, bridge: HubspaceBridge, instance: DebugButtonEnum):
        """Initialize an Afero Button.."""

        self.bridge = bridge
        self.api: AferoBridgeV1 = bridge.api
        self.logger = bridge.logger.getChild("debug-button")
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, bridge.config_entry.data[CONF_USERNAME])},
        )
        self.instance = instance
        self._attr_name = DEVICE_NAMES[instance]
        self._attr_unique_id = (
            f"{bridge.config_entry.data[CONF_USERNAME]}-{instance.value}"
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        data = await self.bridge.api.fetch_data()
        current_path: Path = Path(__file__.rsplit(os.sep, 1)[0])
        if self.instance == DebugButtonEnum.ANON:
            dev_dump = current_path / "_dump_hs_devices.json"
            self.logger.debug("Writing out anonymized device data to %s", dev_dump)
            devs = [get_afero_device(dev) for dev in data]
            async with aiofiles.open(dev_dump, "w") as fh:
                await fh.write(json.dumps(anonymize_devices(devs), indent=4))
        elif self.instance == DebugButtonEnum.RAW:
            data_dump = current_path / "_dump_raw.json"
            self.logger.debug("Writing out raw data to %s", data_dump)
            async with aiofiles.open(data_dump, "w") as fh:
                await fh.write(json.dumps(data, indent=4))
        elif self.instance == DebugButtonEnum.REAUTH:
            self.api.events.emit(EventType.INVALID_AUTH)


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
