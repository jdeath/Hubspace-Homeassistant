"""Platform for fan integration."""

import logging
from contextlib import suppress
from typing import Any, Optional, Union

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_FAN
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


PRESET_HS_TO_HA = {"comfort-breeze": "breeze"}

PRESET_HA_TO_HS = {val: key for key, val in PRESET_HS_TO_HA.items()}


class HubspaceFan(HubSpaceEntity, FanEntity):
    """HubSpace fan that can communicate with Home Assistant


    :ivar _current_direction: Current direction of the device, or if a
        direction change is in progress
    :ivar _fan_speed: Current fan speed
    :ivar _fan_speeds: List of available fan speeds for the device from HubSpace
    :ivar _preset_mode: Current preset mode of the device, such as breeze
    :ivar _preset_modes: List of available preset modes for the device
    :ivar _state: If the device is on / off
    :ivar _supported_features: Features that the fan supports, where each
        feature is an Enum from FanEntityFeature.
    """

    ENTITY_TYPE = ENTITY_FAN
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        device: HubSpaceDevice,
    ) -> None:
        self._state: Optional[str] = None
        self._current_direction: Optional[str] = None
        self._preset_mode: Optional[str] = None
        self._preset_modes: set[str] = set()
        self._supported_features: FanEntityFeature = FanEntityFeature(0)
        self._fan_speeds: list[Union[str, int]] = []
        self._fan_speed: Optional[str] = None
        super().__init__(coordinator, device)

    def process_functions(self, functions: list[dict]) -> None:
        """Process available functions

        :param functions: Functions that are supported from the API
        """
        for function in functions:
            if function["functionInstance"]:
                self._instance_attrs[function["functionClass"]] = function[
                    "functionInstance"
                ]
            if function["functionClass"] == "toggle":
                self._supported_features |= FanEntityFeature.PRESET_MODE
                self._preset_modes.add(function["functionInstance"])
                self._instance_attrs.pop(function["functionClass"])
                _LOGGER.debug(
                    "Adding a new feature - preset, %s", function["functionInstance"]
                )
            elif function["functionClass"] == "fan-speed":
                self._supported_features |= FanEntityFeature.SET_SPEED
                tmp_speed = set()
                for value in function["values"]:
                    if not value["name"].endswith("-000"):
                        tmp_speed.add(value["name"])
                self._fan_speeds = list(sorted(tmp_speed))
                _LOGGER.debug("Adding a new feature - fan speed, %s", self._fan_speeds)
            elif function["functionClass"] == "fan-reverse":
                self._supported_features |= FanEntityFeature.DIRECTION
                _LOGGER.debug("Adding a new feature - direction")
            elif function["functionClass"] == "power":
                _LOGGER.debug("Adding a new feature - on / off")
                # Added in 2024.8.0
                with suppress(AttributeError):
                    self._supported_features |= FanEntityFeature.TURN_ON
                    self._supported_features |= FanEntityFeature.TURN_OFF
            else:
                _LOGGER.debug(
                    "Unsupported feature found, %s", function["functionClass"]
                )
                self._instance_attrs.pop(function["functionClass"], None)

    def update_states(self) -> None:
        """Load initial states into the device"""
        additional_attrs = [
            "wifi-ssid",
            "wifi-mac-address",
            "ble-mac-address",
        ]
        for state in self.get_device_states():
            if state.functionClass == "toggle":
                if state.value == "enabled":
                    self._preset_mode = state.functionInstance
            elif state.functionClass == "fan-speed":
                self._fan_speed = state.value
            elif state.functionClass == "fan-reverse":
                self._current_direction = state.value
            elif state.functionClass == "power":
                self._state = state.value
            elif state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass in additional_attrs:
                self._bonus_attrs[state.functionClass] = state.value

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    @property
    def current_direction(self):
        return self._current_direction

    @property
    def oscillating(self):
        """Determine if the fan is currently oscillating

        I do not believe any HubSpace fan supports oscillation but
        adding in the property.
        """
        return False

    @property
    def percentage(self):
        if self._fan_speed:
            if self._fan_speed.endswith("-000"):
                return 0
            return ordered_list_item_to_percentage(self._fan_speeds, self._fan_speed)
        return 0

    @property
    def preset_mode(self):
        return PRESET_HS_TO_HA.get(self._preset_mode, None)

    @property
    def preset_modes(self):
        return self._preset_modes

    @property
    def speed_count(self):
        return len(self._fan_speeds)

    @property
    def supported_features(self):
        return self._supported_features

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        _LOGGER.debug("Adjusting fan %s with %s", self._child_id, kwargs)
        with suppress(AttributeError):
            if not self._supported_features & FanEntityFeature.TURN_ON:
                raise NotImplementedError
        self._state = "on"
        power_state = HubSpaceState(
            functionClass="power",
            functionInstance=self._instance_attrs.get("power", None),
            value="on",
        )
        await self.set_device_state(power_state)
        await self.async_set_percentage(percentage)
        await self.async_set_preset_mode(preset_mode)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        with suppress(AttributeError):
            if not self._supported_features & FanEntityFeature.TURN_OFF:
                raise NotImplementedError
        self._state = "off"
        power_state = HubSpaceState(
            functionClass="power",
            functionInstance=self._instance_attrs.get("power", None),
            value="off",
        )
        await self.set_device_state(power_state)
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if (
            self._supported_features & FanEntityFeature.SET_SPEED
            and percentage is not None
        ):
            self._fan_speed = percentage_to_ordered_list_item(
                self._fan_speeds, percentage
            )
            speed_state = HubSpaceState(
                functionClass="fan-speed",
                functionInstance=self._instance_attrs.get("fan-speed", None),
                value=self._fan_speed,
            )
            await self.set_device_state(speed_state)
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if self._supported_features & FanEntityFeature.PRESET_MODE:
            if not preset_mode:
                self._preset_mode = None
                preset_state = HubSpaceState(
                    functionClass="toggle",
                    functionInstance=self._preset_mode,
                    value="disabled",
                )
            else:
                self._preset_mode = PRESET_HS_TO_HA.get(preset_mode, None)
                preset_state = HubSpaceState(
                    functionClass="toggle",
                    functionInstance=self._preset_mode,
                    value="enabled",
                )
            await self.set_device_state(preset_state)
            self.async_write_ha_state()

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if self._supported_features & FanEntityFeature.DIRECTION:
            self._current_direction = direction
            direction_state = HubSpaceState(
                functionClass="fan-reverse",
                functionInstance=self._instance_attrs.get("fan-reverse", None),
                value=direction,
            )
            await self.set_device_state(direction_state)
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Fan entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    fans: list[HubspaceFan] = []
    device_registry = dr.async_get(hass)
    for entity in coordinator_hubspace.data[ENTITY_FAN].values():
        _LOGGER.debug("Adding a %s, %s", entity.device_class, entity.friendly_name)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
            manufacturer=entity.manufacturerName,
        )
        ha_entity = HubspaceFan(
            coordinator_hubspace,
            entity,
        )
        fans.append(ha_entity)
    async_add_entities(fans)
