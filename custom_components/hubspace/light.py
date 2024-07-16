"""Platform for light integration."""
from __future__ import annotations

import logging

from .hubspace import HubSpace
from . import hubspace_device
import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_COLOR_TEMP,
    PLATFORM_SCHEMA,
    ColorMode,
    COLOR_MODES_COLOR,
    LightEntity,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import timedelta

# Import exceptions from the requests module
import requests.exceptions

SCAN_INTERVAL = timedelta(seconds=60)
BASE_INTERVAL = timedelta(seconds=60)
SERVICE_NAME = "send_command"
_LOGGER = logging.getLogger(__name__)

CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_DEBUG, default=False): cv.boolean,
        vol.Required(CONF_FRIENDLYNAMES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Required(CONF_ROOMNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


def _brightness_to_hass(value):
    if value is None:
        value = 0
    return int(value) * 255 // 100


def _brightness_to_hubspace(value):
    return value * 100 // 255


def _convert_color_temp(value):
    if isinstance(value, str) and value.endswith("K"):
        value = value[:-1]
    if value is None:
        value = 1
    return 1000000 // int(value)


def create_ha_entity(hs: HubSpace, debug: bool, entity: hubspace_device.HubSpaceDevice):
    """Query HubSpace and find devices to add

    :param hs: HubSpace connection
    :param debug: If debug is enabled
    :param entity: HubSpace API device

    """
    if entity.device_class in ["light", "switch"]:
        return HubspaceLight(
                hs,
                entity.friendly_name,
                debug,
                childId=entity.id,
                model=entity.model,
                deviceId=entity.device_id,
                functions=entity.functions,
            )
    elif entity.device_class == "power-outlet":
        for function in entity.functions:
            if function.get("functionClass") == "toggle":
                try:
                    _LOGGER.debug(
                        f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}"
                    )
                    outletIndex = function.get("functionInstance").split("-")[1]
                    return HubspaceOutlet(
                        hs,
                        entity.friendly_name,
                        outletIndex,
                        debug,
                        childId=entity.id,
                        model=entity.model,
                        deviceId=entity.device_id,
                        deviceClass=entity.device_class,
                    )
                except IndexError:
                    _LOGGER.debug("Error extracting outlet index")
    elif entity.device_class == "landscape-transformer":
        for function in entity.functions:
            if function.get("functionClass") == "toggle":
                try:
                    _LOGGER.debug(
                        f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}"
                    )
                    outletIndex = function.get("functionInstance").split("-")[1]
                    return HubspaceTransformer(
                        hs,
                        entity.friendly_name,
                        outletIndex,
                        debug,
                        childId=entity.id,
                        model=entity.model,
                        deviceId=entity.device_id,
                        deviceClass=entity.device_class,
                    )
                except IndexError:
                    _LOGGER.debug("Error extracting outlet index")
    elif entity.device_class == "water-timer":
        for function in entity.functions:
            if function.get("functionClass") == "toggle":
                try:
                    _LOGGER.debug(
                        f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}"
                    )
                    outletIndex = function.get("functionInstance").split("-")[1]
                    return HubspaceTransformer(
                        hs,
                        entity.friendly_name,
                        outletIndex,
                        debug,
                        childId=entity.id,
                        model=entity.model,
                        deviceId=entity.device_id,
                        deviceClass=entity.device_class,
                    )
                except IndexError:
                    _LOGGER.debug("Error extracting outlet index")
    elif entity.device_class == "fan":
        return HubspaceFan(
                hs,
                entity.friendly_name,
                debug,
                childId=entity.id,
                model=entity.model,
                deviceId=entity.device_id,
                deviceClass=entity.device_class,
            )
    else:
        _LOGGER.debug(f"Unable to process the entity {entity.friendly_name} of class {entity.device_class}")


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Awesome Light platform."""

    # Assign configuration variables.
    # The configuration check takes care they are present.

    username = config[CONF_USERNAME]
    password = config.get(CONF_PASSWORD)
    debug = config.get(CONF_DEBUG)
    try:
        hs = HubSpace(username, password)
    except requests.exceptions.ReadTimeout as ex:
        # Where does this exception come from? The integration will break either way
        # but more spectacularly since the exception is not imported
        raise PlatformNotReady(
            f"Connection error while connecting to hubspace: {ex}"
        ) from ex

    entities = []
    friendly_names: list[str] = config.get(CONF_FRIENDLYNAMES, [])
    room_names: list[str] = config.get(CONF_ROOMNAMES, [])
    data = hubspace_device.get_devices_cached(hs)
    for entity in hubspace_device.get_hubspace_devices(data, friendly_names, room_names):
        ha_entity = create_ha_entity(hs, debug, entity)
        if ha_entity:
            _LOGGER.debug(f"Adding an entity {ha_entity._childId}")
            entities.append(ha_entity)
    add_entities(entities)


    def my_service(call: ServiceCall) -> None:
        """My first service."""
        _LOGGER.info("Received data" + str(call.data))
        name = SERVICE_NAME
        entity_ids = call.data["entity_id"]
        functionClass = call.data["functionClass"]
        value = call.data["value"]

        if "functionInstance" in call.data:
            functionInstance = call.data["functionInstance"]
        else:
            functionInstance = None

        for entity_id in entity_ids:
            _LOGGER.info("entity_id: " + str(entity_id))
            for i in entities:
                if i.entity_id == entity_id:
                    _LOGGER.info("Found Entity")
                    i.send_command(functionClass, value, functionInstance)

    # Register our service with Home Assistant.
    hass.services.register("hubspace", "send_command", my_service)


def process_color_temps(color_temps: dict) -> list[int]:
    """Determine the supported color temps

    :param color_temps: Result from functions["values"]
    """
    supported_temps = []
    for temp in color_temps:
        color_temp = temp["name"]
        if color_temp.endswith("K"):
            color_temp = int(color_temp[:-1])
        supported_temps.append(color_temp)
    return sorted(supported_temps)


def process_brightness(brightness: dict) -> list[int]:
    """Determine the supported brightness levels

    :param brightness: Result from functions["values"]
    """
    supported_brightness = []
    brightness_min = brightness["range"]["min"]
    brightness_max = brightness["range"]["max"]
    brightness_step = brightness["range"]["step"]
    if brightness_min == brightness_max:
        supported_brightness.append(brightness_max)
    else:
        for brightness in range(brightness_min, brightness_max, brightness_step):
            supported_brightness.append(brightness)
        if brightness_max not in supported_brightness:
            supported_brightness.append(brightness_max)
    return supported_brightness


class HubspaceLight(LightEntity):
    """Representation of a HubSpace Light"""

    def __init__(
        self,
        hs,
        friendlyname,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        functions=None,
    ) -> None:
        self._name = friendlyname

        self._debug = debug
        self._state = "off"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePowerFunctionInstance = None
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None

        # colorMode == 'color' || 'white'
        self._colorMode = None
        self._colorTemp = None
        self._rgbColor = None
        self._temperature_choices = None
        self._temperature_suffix = None
        self._supported_color_modes = set(ColorMode.ONOFF)
        self._supported_brightness = []

        if functions:
            self.process_functions(functions)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )


    def process_functions(self, functions: list[dict]) -> None:
        """Process the functions and configure the light attributes

        :param functions: Functions that are supported from the API
        """
        for function in functions:
            if function["functionClass"] == "power":
                self._usePowerFunctionInstance = function.get("functionInstance", None)
            elif function["functionClass"] == "color-temperature":
                self._temperature_choices = process_color_temps(function["values"])
                if self._temperature_choices:
                    self._supported_color_modes.add(ColorMode.COLOR_TEMP)
                    self._temperature_suffix = "K"
            elif function["functionClass"] == "brightness":
                temp_bright = process_brightness(function["values"][0])
                if temp_bright:
                    self._supported_brightness = temp_bright
                    self._supported_color_modes.add(ColorMode.BRIGHTNESS)

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId

    @property
    def color_mode(self) -> ColorMode:
        if self._colorMode == "color":
            return ColorMode.RGB
        return self._colorMode

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {*self._supported_color_modes}

    @property
    def brightness(self) -> int or None:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    @property
    def min_color_temp_kelvin(self) -> int:
        return min(self._temperature_choices)

    @property
    def max_color_temp_kelvin(self) -> int:
        return max(self._temperature_choices)

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    def turn_on(self, **kwargs: Any) -> None:
        """Perform power on and set additional attributes"""
        _LOGGER.debug(f"Adjusting light {self._childId} with {kwargs}")
        power_state = {
            "functionClass": "power",
            "value": "on",
        }
        if self._usePowerFunctionInstance:
            power_state["functionInstance"] = self._usePowerFunctionInstance
        states_to_set = [power_state]
        if ATTR_BRIGHTNESS in kwargs and ColorMode.BRIGHTNESS in self._supported_color_modes:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            states_to_set.append(
                {
                    "functionClass": "brightness",
                    "value": _brightness_to_hubspace(brightness),
                }
            )
        if ATTR_COLOR_TEMP in kwargs and ColorMode.COLOR_TEMP in self._supported_color_modes:
            color_to_set = self._temperature_choices[0]
            # I am not sure how to set specific values, so find the value
            # that is closest without going over
            for color in self._temperature_choices:
                if kwargs[ATTR_COLOR_TEMP_KELVIN] <= color:
                    color_to_set = color
                    break
            states_to_set.append(
                {
                    "functionClass": "color-temperature",
                    "value": f"{color_to_set}K",
                }
            )
        self._hs.set_states(self._childId, states_to_set)

    @property
    def rgb_color(self):
        """Return the rgb value."""
        return self._rgbColor

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        attr["deviceId"] = self._deviceId
        attr["devbranch"] = False

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setPowerState(
            self._childId, "off", self._usePowerFunctionInstance
        )

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        for state in self._hs.get_states(self._childId)["values"]:
            if state["functionClass"] == "power":
                self._state = state["value"]
            elif state["functionClass"] == "color-temperature":
                tmp_state = state["value"]
                if tmp_state.endswith("K"):
                    tmp_state = tmp_state[:-1]
                self._colorTemp = tmp_state
            elif state["functionClass"] == "brightness":
                self._brightness = _brightness_to_hass(state["value"])
            elif state["functionClass"] == "color-mode":
                self._colorMode = state["value"]
            elif state["functionClass"] == "color-rgb":
                self._colorMode = (
                    int(state.get("color-rgb").get("r")),
                    int(state.get("color-rgb").get("g")),
                    int(state.get("color-rgb").get("b"))
                )


class HubspaceOutlet(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        hs,
        friendlyname,
        outletIndex,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        deviceClass=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        self._name = friendlyname + "_outlet_" + outletIndex

        self._debug = debug
        self._state = "off"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None
        self._outletIndex = outletIndex

        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(friendlyname)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId + "_" + self._outletIndex

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(
            self._childId, "toggle", "outlet-" + self._outletIndex, "on"
        )
        #self.update()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        attr["deviceId"] = self._deviceId + "_" + self._outletIndex
        attr["devbranch"] = False

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(
            self._childId, "toggle", "outlet-" + self._outletIndex, "off"
        )
        #self.update()

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(
            self._childId, "toggle", "outlet-" + self._outletIndex
        )
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)


class HubspaceFan(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        hs,
        friendlyname,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        deviceClass=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        if None in (childId, model, deviceId, deviceClass):
            self._name = friendlyname + "_fan"
        else:
            self._name = friendlyname

        self._debug = debug
        self._state = "off"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None

        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(friendlyname)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId + "_fan"

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId, "power", "fan-power", "on")

        # Homeassistant uses 0-255
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        brightnessPercent = _brightness_to_hubspace(brightness)


        if self._model == "DriskolFan":
            if brightnessPercent < 40:
                speed = "020"
            elif brightnessPercent < 50:
                speed = "040"
            elif brightnessPercent < 70:
                speed = "060"
            elif brightnessPercent < 90:
                speed = "080"
            else:
                speed = "100"
            speedstring = "fan-speed-5-" + speed
        elif self._model == "CF2003":
            if brightnessPercent < 20:
                speed = "016"
            if brightnessPercent < 40:
                speed = "033"
            elif brightnessPercent < 55:
                speed = "050"
            elif brightnessPercent < 75:
                speed = "066"
            elif brightnessPercent < 90:
                speed = "083"
            else:
                speed = "100"
            speedstring = "fan-speed-6-" + speed
        elif self._model == "NevaliFan":
            if brightnessPercent < 40:
                speed = "033"
            elif brightnessPercent < 75:
                speed = "066"
            else:
                speed = "100"
            speedstring = "fan-speed-3-" + speed
        elif self._model == "TagerFan":
            if brightnessPercent < 25:
                speed = "020"
            elif brightnessPercent < 35:
                speed = "030"
            elif brightnessPercent < 45:
                speed = "040"
            elif brightnessPercent < 55:
                speed = "050"
            elif brightnessPercent < 65:
                speed = "060"
            elif brightnessPercent < 75:
                speed = "070"
            elif brightnessPercent < 85:
                speed = "080"
            elif brightnessPercent < 95:
                speed = "090"
            else:
                speed = "100"
            speedstring = "fan-speed-9-" + speed
        else:
            if brightnessPercent < 30:
                speed = "025"
            elif brightnessPercent < 60:
                speed = "050"
            elif brightnessPercent < 85:
                speed = "075"
            else:
                speed = "100"
            speedstring = "fan-speed-" + speed

        self._hs.setStateInstance(self._childId, "fan-speed", "fan-speed", speedstring)
        #self.update()

    @property
    def color_mode(self) -> ColorMode:
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    @property
    def brightness(self) -> int or None:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        if self._name.endswith("_fan"):
            attr["deviceId"] = self._deviceId + "_fan"
        else:
            attr["deviceId"] = self._deviceId
        attr["devbranch"] = False

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(self._childId, "power", "fan-power", "off")
        if self._model != "DriskolFan":
            self._hs.setStateInstance(
                self._childId, "fan-speed", "fan-speed", "fan-speed-000"
            )
        else:
            self._hs.setStateInstance(
                self._childId, "fan-speed", "fan-speed", "fan-speed-5-000"
            )
        #self.update()

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(self._childId, "power", "fan-power")
        fanspeed = self._hs.getStateInstance(self._childId, "fan-speed", "fan-speed")
        brightness = 0

        if fanspeed == "fan-speed-000":
            brightness = 0
        elif fanspeed == "fan-speed-025":
            brightness = 63
        elif fanspeed == "fan-speed-050":
            brightness = 127
        elif fanspeed == "fan-speed-075":
            brightness = 191
        elif fanspeed == "fan-speed-100":
            brightness = 255

        if fanspeed == "fan-speed-5-000":
            brightness = 0
        elif fanspeed == "fan-speed-5-020":
            brightness = 51
        elif fanspeed == "fan-speed-5-040":
            brightness = 102
        elif fanspeed == "fan-speed-5-060":
            brightness = 153
        elif fanspeed == "fan-speed-5-080":
            brightness = 204
        elif fanspeed == "fan-speed-100":
            brightness = 255

        if fanspeed == "fan-speed-6-000":
            brightness = 0
        elif fanspeed == "fan-speed-6-016":
            brightness = 51
        elif fanspeed == "fan-speed-6-033":
            brightness = 102
        elif fanspeed == "fan-speed-6-050":
            brightness = 128
        elif fanspeed == "fan-speed-6-066":
            brightness = 153
        elif fanspeed == "fan-speed-6-083":
            brightness = 204
        elif fanspeed == "fan-speed-6-100":
            brightness = 255

        if fanspeed == "fan-speed-000":
            brightness = 0
        elif fanspeed == "fan-speed-3-033":
            brightness = 102
        elif fanspeed == "fan-speed-3-066":
            brightness = 153
        elif fanspeed == "fan-speed-3-100":
            brightness = 255

        # For Tager Fan
        if fanspeed == "fan-speed-000":
            brightness = 0
        elif fanspeed == "fan-speed-9-020":
            brightness = 50
        elif fanspeed == "fan-speed-9-030":
            brightness = 75
        elif fanspeed == "fan-speed-9-040":
            brightness = 100
        elif fanspeed == "fan-speed-9-050":
            brightness = 125
        elif fanspeed == "fan-speed-9-060":
            brightness = 150
        elif fanspeed == "fan-speed-9-070":
            brightness = 175
        elif fanspeed == "fan-speed-9-080":
            brightness = 200
        elif fanspeed == "fan-speed-9-090":
            brightness = 225
        elif fanspeed == "fan-speed-9-100":
            brightness = 255

        self._brightness = brightness

        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)


class HubspaceTransformer(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        hs,
        friendlyname,
        outletIndex,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        deviceClass=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        self._name = friendlyname + "_transformer_" + outletIndex

        self._debug = debug
        self._state = "off"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None
        self._watts = None
        self._volts = None

        self._outletIndex = outletIndex
        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(friendlyname)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId + "_" + self._outletIndex

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(
            self._childId, "toggle", "zone-" + self._outletIndex, "on"
        )
        #self.update()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        attr["deviceId"] = self._deviceId + "_" + self._outletIndex
        attr["devbranch"] = False
        attr["watts"] = self._watts
        attr["volts"] = self._volts

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(
            self._childId, "toggle", "zone-" + self._outletIndex, "off"
        )
        #self.update()

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(
            self._childId, "toggle", "zone-" + self._outletIndex
        )

        if self._outletIndex == "1":
            self._watts = self._hs.getState(self._childId, "watts")
            self._volts = self._hs.getState(self._childId, "output-voltage-switch")

        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)


class HubspaceLock(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        hs,
        friendlyname,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        deviceClass=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        self._name = friendlyname

        self._debug = debug
        self._state = "unlocked"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None
        self._batterylevel = None
        self._lastevent = None

        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(friendlyname)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "locked"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setState(self._childId, "lock-control", "locking")
        self._state = "locked"
        #self.update()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        attr["deviceId"] = self._deviceId
        attr["devbranch"] = False
        attr["battery-level"] = self._batterylevel
        attr["last-event"] = self._lastevent

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setState(self._childId, "lock-control", "unlocking")
        self._state = "unlocked"
        #self.update()

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getState(self._childId, "lock-control")

        self._batterylevel = self._hs.getState(self._childId, "battery-level")
        self._lastevent = self._hs.getState(self._childId, "last-event")

        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)

class HubspaceWaterTimer(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(
        self,
        hs,
        friendlyname,
        outletIndex,
        debug,
        childId=None,
        model=None,
        deviceId=None,
        deviceClass=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        self._name = friendlyname + "_spigot_" + outletIndex

        self._debug = debug
        self._state = "off"
        self._childId = childId
        self._model = model
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None
        self._outletIndex = outletIndex

        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(friendlyname)

    async def async_setup_entry(hass, entry):
        """Set up the media player platform for Sonos."""

        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "send_command",
            {
                vol.Required("functionClass"): cv.string,
                vol.Required("value"): cv.string,
                vol.Optional("functionInstance"): cv.string,
            },
            "send_command",
        )

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._childId + "_" + self._outletIndex

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(
            self._childId, "toggle", "spigot-" + self._outletIndex, "on"
        )
        #self.update()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"] = self._model
        attr["deviceId"] = self._deviceId + "_" + self._outletIndex
        attr["devbranch"] = False

        attr["debugInfo"] = self._debugInfo

        return attr

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(
            self._childId, "toggle", "spigot-" + self._outletIndex, "off"
        )
        #self.update()

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(
            self._childId, "toggle", "spigot-" + self._outletIndex
        )
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)
