"""Platform for fan integration."""

import logging
from contextlib import suppress
from typing import Any, Optional, Union

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, ENTITY_FAN

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.fan import FanEntity, FanEntityFeature
from hubspace_async import HubSpaceState

from . import HubSpaceConfigEntry
from .coordinator import HubSpaceDataUpdateCoordinator

PRESET_HS_TO_HA = {"comfort-breeze": "breeze"}

PRESET_HA_TO_HS = {val: key for key, val in PRESET_HS_TO_HA.items()}


class HubspaceFan(CoordinatorEntity, FanEntity):
    """HubSpace fan that can communicate with Home Assistant

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _state: If the device is on / off
    :ivar _current_direction: Current direction of the device, or if a
        direction change is in progress
    :ivar _preset_mode: Current preset mode of the device, such as breeze
    :ivar _preset_modes: List of available preset modes for the device
    :ivar _supported_features: Features that the fan supports, where each
        feature is an Enum from FanEntityFeature.
    :ivar _fan_speeds: List of available fan speeds for the device from HubSpace
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _instance_attrs: Additional attributes that are required when
        POSTing to HubSpace

    :param hs: HubSpace connector
    :param friendly_name: The friendly name of the device
    :param child_id: ID used when making requests to HubSpace
    :param model: Model of the device
    :param device_id: Parent Device ID
    :param functions: List of supported functions for the device
    """

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        hs: HubSpaceDataUpdateCoordinator,
        friendly_name: str,
        child_id: Optional[str] = None,
        model: Optional[str] = None,
        device_id: Optional[str] = None,
        functions: Optional[list[dict]] = None,
    ) -> None:
        self._name: str = friendly_name
        self.coordinator = hs
        self._hs = hs.conn
        self._child_id: str = child_id
        self._state: Optional[str] = None
        self._current_direction: Optional[str] = None
        self._preset_mode: Optional[str] = None
        self._preset_modes: set[str] = set()
        self._supported_features: FanEntityFeature = FanEntityFeature(0)
        self._fan_speeds: list[Union[str, int]] = []
        self._fan_speed: Optional[str] = None
        self._bonus_attrs = {
            "model": model,
            "deviceId": device_id,
            "Child ID": self._child_id,
        }
        self._instance_attrs: dict[str, str] = {}
        functions = functions or []
        self.process_functions(functions)
        super().__init__(hs, context=self._child_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

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
                # This code is in the mainline but unreleased
                with suppress(AttributeError):
                    self._supported_features |= FanEntityFeature.TURN_ON
                    self._supported_features |= FanEntityFeature.TURN_OFF
            else:
                _LOGGER.debug("Unsupported feature found, %s", function["functionClass"])
                self._instance_attrs.pop(function["functionClass"], None)

    def update_states(self) -> None:
        """Load initial states into the device"""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_FAN][self._child_id].states
        additional_attrs = [
            "wifi-ssid",
            "wifi-mac-address",
            "available",
            "ble-mac-address",
        ]
        # functionClass -> internal attribute
        for state in states:
            if state.functionClass == "toggle":
                if state.value == "enabled":
                    self._preset_mode = state.functionInstance
            elif state.functionClass == "fan-speed":
                self._fan_speed = state.value
            elif state.functionClass == "fan-reverse":
                self._current_direction = state.value
            elif state.functionClass == "power":
                self._state = state.value
            elif state.functionClass in additional_attrs:
                self._bonus_attrs[state.functionClass] = state.value

    @property
    def should_poll(self):
        return False

    # Entity-specific properties
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._child_id

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._bonus_attrs

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._bonus_attrs["deviceId"])},
            name=self._name,
            model=self._bonus_attrs["model"],
        )

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
        _LOGGER.debug(f"Adjusting fan {self._child_id} with {kwargs}")
        with suppress(AttributeError):
            if not self._supported_features & FanEntityFeature.TURN_ON:
                raise NotImplementedError
        self._state = "on"
        power_state = HubSpaceState(
            functionClass="power",
            functionInstance=self._instance_attrs.get("power", None),
            value="on",
        )
        await self._hs.set_device_state(self._child_id, power_state)
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
        await self._hs.set_device_state(self._child_id, power_state)
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
            await self._hs.set_device_state(self._child_id, speed_state)
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
            await self._hs.set_device_state(self._child_id, preset_state)
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
            await self._hs.set_device_state(self._child_id, direction_state)
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
        _LOGGER.debug(f"Adding a {entity.device_class}, {entity.friendly_name}")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
        )
        ha_entity = HubspaceFan(
            coordinator_hubspace,
            entity.friendly_name,
            child_id=entity.id,
            model=entity.model,
            device_id=entity.device_id,
            functions=entity.functions,
        )
        fans.append(ha_entity)
    async_add_entities(fans)
