"""Platform for fan integration."""

import dataclasses
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_LIGHT

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from hubspace_async import HubSpaceState

from . import HubSpaceConfigEntry
from .coordinator import HubSpaceDataUpdateCoordinator


def _brightness_to_hass(value):
    if value is None:
        value = 0
    return int(value) * 255 // 100


def _brightness_to_hubspace(value):
    return value * 100 // 255


def process_range(range_vals: dict) -> list[Any]:
    """Process a range to determine what's supported

    :param range_vals: Result from functions["values"][x]
    """
    supported_range = []
    range_min = range_vals["range"]["min"]
    range_max = range_vals["range"]["max"]
    range_step = range_vals["range"]["step"]
    if range_min == range_max:
        supported_range.append(range_max)
    else:
        for brightness in range(range_min, range_max, range_step):
            supported_range.append(brightness)
        if range_max not in supported_range:
            supported_range.append(range_max)
    return supported_range


@dataclasses.dataclass
class RGB:
    red: int = 0
    green: int = 0
    blue: int = 0


def process_color_temps(color_temps: dict) -> tuple[list[int], str]:
    """Determine the supported color temps

    :param color_temps: Result from functions["values"]
    """
    supported_temps = []
    prefix = ""
    for temp in color_temps:
        color_temp = temp["name"]
        if isinstance(color_temp, str) and color_temp.endswith("K"):
            prefix = "k"
            color_temp = color_temp[0:-1]
        supported_temps.append(int(color_temp))
    return sorted(supported_temps), prefix


class HubspaceLight(CoordinatorEntity, LightEntity):
    """HubSpace light that can communicate with Home Assistant

    @TODO - Support for HS, RGB, RGBW, RGBWW, XY

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _state: If the device is on / off
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _instance_attrs: Additional attributes that are required when
        POSTing to HubSpace
    :ivar _color_modes: Supported options for the light
    :ivar _color_mode: Current color mode of the light
    :ivar _color_temp: Current temperature of the light
    :ivar _temperature_choices: Supported temperatures of the light
    :ivar _temperature_prefix: Prefix for HubSpace
    :ivar _brightness: Current brightness of the light
    :ivar _supported_brightness: Supported brightness of the light
    :ivar _rgb: Current RGB values


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
        self._bonus_attrs = {
            "model": model,
            "deviceId": device_id,
            "Child ID": self._child_id,
        }
        self._instance_attrs: dict[str, str] = {}
        # Entity-specific
        self._color_modes: set[ColorMode] = set()
        self._color_mode: ColorMode = ColorMode.UNKNOWN
        self._color_temp: Optional[int] = None
        self._temperature_choices: Optional[set[Any]] = set()
        self._temperature_prefix: str = ""
        self._supported_brightness: Optional[list[int]] = []
        self._brightness: Optional[int] = None
        self._rgb: RGB = RGB(red=0, green=0, blue=0)

        functions = functions or []
        self.process_functions(functions)
        self._adjust_supported_modes()
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
            if function.get("functionInstance"):
                self._instance_attrs[function["functionClass"]] = function[
                    "functionInstance"
                ]
            if function["functionClass"] == "power":
                self._color_modes.add(ColorMode.ONOFF)
                _LOGGER.debug("Adding a new feature - on / off")
            elif function["functionClass"] == "color-temperature":
                self._temperature_choices, self._temperature_prefix = (
                    process_color_temps(function["values"])
                )
                if self._temperature_choices:
                    self._color_modes.add(ColorMode.COLOR_TEMP)
                    _LOGGER.debug("Adding a new feature - color temperature")
            elif function["functionClass"] == "brightness":
                temp_bright = process_range(function["values"][0])
                if temp_bright:
                    self._supported_brightness = temp_bright
                    self._color_modes.add(ColorMode.BRIGHTNESS)
                    _LOGGER.debug("Adding a new feature - brightness")
            elif function["functionClass"] == "color-rgb":
                self._color_modes.add(ColorMode.RGB)
                _LOGGER.debug("Adding a new feature - rgb")
            else:
                _LOGGER.debug("Unsupported feature found, %s", function["functionClass"])
                self._instance_attrs.pop(function["functionClass"], None)

    def update_states(self) -> None:
        """Load initial states into the device"""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_LIGHT][self._child_id].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._child_id
            )
        additional_attrs = []
        # functionClass -> internal attribute
        for state in states:
            if state.functionClass == "power":
                self._state = state.value
            elif state.functionClass == "color-temperature":
                if isinstance(state.value, str) and state.value.endswith("K"):
                    state.value = state.value[0:-1]
                self._color_temp = int(state.value)
            elif state.functionClass == "brightness":
                self._brightness = _brightness_to_hass(state.value)
            elif state.functionClass == "color-mode":
                self._color_mode = state.value
            elif state.functionClass == "color-rgb":
                self._rgb = RGB(
                    red=state.value["color-rgb"].get("r", 0),
                    green=state.value["color-rgb"].get("g", 0),
                    blue=state.value["color-rgb"].get("b", 0),
                )
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
            name=self.name,
            model=self._bonus_attrs["model"],
        )

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        if not self._color_modes:
            return {ColorMode.UNKNOWN}
        else:
            return {*self._color_modes}

    @property
    def color_mode(self) -> ColorMode | str | None:
        if len(self._color_modes) == 1 and not self._color_mode:
            return list(self._color_modes)[0]
        else:
            return self._color_mode

    @property
    def brightness(self) -> int or None:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def min_color_temp_kelvin(self) -> int:
        return min(self._temperature_choices)

    @property
    def max_color_temp_kelvin(self) -> int:
        return max(self._temperature_choices)

    @property
    def color_temp_kelvin(self) -> int:
        return self._color_temp

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return (
            self._rgb.red,
            self._rgb.green,
            self._rgb.blue,
        )

    # Entity-specific functions
    def _adjust_supported_modes(self):
        """Lights are annoying"""
        mode_temp = {ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP}
        mode_bright = {ColorMode.BRIGHTNESS, ColorMode.ONOFF}
        if mode_temp & self._color_modes == mode_temp:
            self._color_modes.remove(ColorMode.BRIGHTNESS)
        if mode_bright & self._color_modes == mode_bright:
            self._color_modes.remove(ColorMode.ONOFF)
        if len(self._color_modes) > 1 and ColorMode.ONOFF in self._color_modes:
            self._color_modes.remove(ColorMode.ONOFF)

    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"Adjusting light {self._child_id} with {kwargs}")
        self._state = "on"
        states_to_set = [
            HubSpaceState(
                functionClass="power",
                functionInstance=self._instance_attrs.get("power", None),
                value="on",
            )
        ]
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            states_to_set.append(
                HubSpaceState(
                    functionClass="brightness",
                    functionInstance=self._instance_attrs.get("brightness", None),
                    value=_brightness_to_hubspace(brightness),
                )
            )
            self._brightness = brightness
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            color_to_set = list(self._temperature_choices)[0]
            # I am not sure how to set specific values, so find the value
            # that is closest without going over
            for temperature in self._temperature_choices:
                if kwargs[ATTR_COLOR_TEMP_KELVIN] <= temperature:
                    color_to_set = temperature
                    break
                states_to_set.append(
                    HubSpaceState(
                        functionClass="color-temperature",
                        functionInstance=self._instance_attrs.get(
                            "color-temperature", None
                        ),
                        value=f"{temperature}{self._temperature_prefix}",
                    )
                )
            self._color_temp = color_to_set
        if ATTR_RGB_COLOR in kwargs:
            self._rgb = RGB(
                red=kwargs[ATTR_RGB_COLOR][0],
                green=kwargs[ATTR_RGB_COLOR][1],
                blue=kwargs[ATTR_RGB_COLOR][2],
            )
            states_to_set.append(
                HubSpaceState(
                    functionClass="color-rgb",
                    functionInstance=self._instance_attrs.get("color-rgb", None),
                    value=kwargs[ATTR_RGB_COLOR],
                )
            )
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.debug(f"Adjusting light {self._child_id} with {kwargs}")
        self._state = "off"
        states_to_set = [
            HubSpaceState(
                functionClass="power",
                functionInstance=self._instance_attrs.get("power", None),
                value=self._state,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
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
    entities: list[HubspaceLight] = []
    device_registry = dr.async_get(hass)
    for entity in coordinator_hubspace.data[ENTITY_LIGHT].values():
        _LOGGER.debug(f"Adding a {entity.device_class}, {entity.friendly_name}")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
        )
        ha_entity = HubspaceLight(
            coordinator_hubspace,
            entity.friendly_name,
            child_id=entity.id,
            model=entity.model,
            device_id=entity.device_id,
            functions=entity.functions,
        )
        entities.append(ha_entity)
    async_add_entities(entities)
