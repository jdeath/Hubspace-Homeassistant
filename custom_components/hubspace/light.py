"""Platform for light integration."""
from __future__ import annotations

import logging

from .hubspace import HubSpace
import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_WHITE,
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


def _add_entity(entities, hs, model, deviceClass, friendlyName, debug):

    if model == "HPKA315CWB" or model == "HPPA52CWBA023":
        _LOGGER.debug("Creating Outlets")
        entities.append(HubspaceOutlet(hs, friendlyName, "1", debug))
        entities.append(HubspaceOutlet(hs, friendlyName, "2", debug))
    elif model == "LTS-4G-W":
        _LOGGER.debug("Creating Outlets")
        entities.append(HubspaceOutlet(hs, friendlyName, "1", debug))
        entities.append(HubspaceOutlet(hs, friendlyName, "2", debug))
        entities.append(HubspaceOutlet(hs, friendlyName, "3", debug))
        entities.append(HubspaceOutlet(hs, friendlyName, "4", debug))
    elif model == "HB-200-1215WIFIB":
        _LOGGER.debug("Creating Transformers")
        entities.append(HubspaceTransformer(hs, friendlyName, "1", debug))
        entities.append(HubspaceTransformer(hs, friendlyName, "2", debug))
        entities.append(HubspaceTransformer(hs, friendlyName, "3", debug))
    elif model == "52133, 37833":
        _LOGGER.debug("Creating Fan")
        entities.append(HubspaceFan(hs, friendlyName, debug))
        _LOGGER.debug("Creating Light")
        entities.append(HubspaceLight(hs, friendlyName, debug))
    elif model == "76278, 37278":
        _LOGGER.debug("Creating Fan")
        entities.append(HubspaceFan(hs, friendlyName, debug))
        _LOGGER.debug("Creating Light")
        entities.append(HubspaceLight(hs, friendlyName, debug))
    elif model == "DriskolFan":
        _LOGGER.debug("Creating Fan")
        entities.append(HubspaceFan(hs, friendlyName, debug))
        _LOGGER.debug("Creating Light")
        entities.append(HubspaceLight(hs, friendlyName, debug))    
    elif deviceClass == "door-lock" and model == "TBD":
        _LOGGER.debug("Creating Lock")
        entities.append(HubspaceLock(hs, friendlyName, debug))
    else:
        _LOGGER.debug("creating lights")
        entities.append(HubspaceLight(hs, friendlyName, debug))

    return entities


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
        raise PlatformNotReady(
            f"Connection error while connecting to hubspace: {ex}"
        ) from ex

    entities = []
    for friendlyName in config.get(CONF_FRIENDLYNAMES):

        _LOGGER.debug("friendlyName " + friendlyName)
        [childId, model, deviceId, deviceClass] = hs.getChildId(friendlyName)

        _LOGGER.debug("Switch on Model " + model)
        _LOGGER.debug("childId: " + childId)
        _LOGGER.debug("deviceId: " + deviceId)
        _LOGGER.debug("deviceClass: " + deviceClass)
        
        if deviceClass == "fan" and model == "":
            model == "DriskolFan"
            
        entities = _add_entity(entities, hs, model, deviceClass, friendlyName, debug)

    for roomName in config.get(CONF_ROOMNAMES):

        _LOGGER.debug("roomName " + roomName)
        children = hs.getChildrenFromRoom(roomName)

        for childId in children:

            _LOGGER.debug("childId " + childId)
            [childId, model, deviceId, deviceClass, friendlyName] = hs.getChildInfoById(
                childId
            )

            _LOGGER.debug("Switch on Model " + model)
            _LOGGER.debug("deviceId: " + deviceId)
            _LOGGER.debug("deviceClass: " + deviceClass)
            _LOGGER.debug("friendlyName: " + friendlyName)
            
            if deviceClass == "fan" and model == "":
                model == "DriskolFan"
            
            entities = _add_entity(
                entities, hs, model, deviceClass, friendlyName, debug
            )

    if config.get(CONF_FRIENDLYNAMES) == [] and config.get(CONF_ROOMNAMES) == []:
        _LOGGER.debug("Attempting automatic discovery")
        for [
            childId,
            model,
            deviceId,
            deviceClass,
            friendlyName,
            functions,
        ] in hs.discoverDeviceIds():
            _LOGGER.debug("childId " + childId)
            _LOGGER.debug("Switch on Model " + model)
            _LOGGER.debug("deviceId: " + deviceId)
            _LOGGER.debug("deviceClass: " + deviceClass)
            _LOGGER.debug("friendlyName: " + friendlyName)
            _LOGGER.debug("functions: " + str(functions))

            if deviceClass == "fan":
                if model == "":
                    model == "DriskolFan"
                entities.append(
                    HubspaceFan(
                        hs, friendlyName, debug, childId, model, deviceId, deviceClass
                    )
                )
            elif deviceClass == "light" or deviceClass == "switch":
                entities.append(
                    HubspaceLight(
                        hs,
                        friendlyName,
                        debug,
                        childId,
                        model,
                        deviceId,
                        deviceClass,
                        functions,
                    )
                )
            elif deviceClass == "power-outlet":
                for function in functions:
                    if function.get("functionClass") == "toggle":
                        try:
                            _LOGGER.debug(
                                f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}"
                            )
                            outletIndex = function.get("functionInstance").split("-")[1]
                            entities.append(
                                HubspaceOutlet(
                                    hs,
                                    friendlyName,
                                    outletIndex,
                                    debug,
                                    childId,
                                    model,
                                    deviceId,
                                    deviceClass,
                                )
                            )
                        except IndexError:
                            _LOGGER.debug("Error extracting outlet index")
            elif deviceClass == "landscape-transformer":
                for function in functions:
                    if function.get("functionClass") == "toggle":
                        try:
                            _LOGGER.debug(
                                f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}"
                            )
                            outletIndex = function.get("functionInstance").split("-")[1]
                            entities.append(
                                HubspaceTransformer(
                                    hs,
                                    friendlyName,
                                    outletIndex,
                                    debug,
                                    childId,
                                    model,
                                    deviceId,
                                    deviceClass,
                                )
                            )
                        except IndexError:
                            _LOGGER.debug("Error extracting outlet index")

    if not entities:
        return
    add_entities(entities)

    def my_service(call: ServiceCall) -> None:
        """My first service."""
        _LOGGER.info("Received data" + str(call.data))

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


class HubspaceLight(LightEntity):
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
        functions=None,
    ) -> None:
        """Initialize an AwesomeLight."""

        _LOGGER.debug("Light Name: ")
        _LOGGER.debug(friendlyname)
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
        self._min_mireds = None
        self._max_mireds = None
        self._rgbColor = None
        self._temperature_choices = None
        self._temperature_suffix = None
        if None in (childId, model, deviceId, deviceClass):
            [
                self._childId,
                self._model,
                self._deviceId,
                deviceClass,
            ] = self._hs.getChildId(self._name)
        if functions is None:
            functions = self._hs.getFunctions(self._childId)

        self._supported_color_modes = []

        # https://www.homedepot.com/p/Commercial-Electric-500-Watt-Single-Pole-Smart-Hubspace-Dimmer-with-Motion-Sensor-White-HPDA311CWB/317249353
        if self._model == "HPDA311CWB":
            self._supported_color_modes.extend([ColorMode.BRIGHTNESS])

        # https://www.homedepot.com/p/Defiant-15-Amp-120-Volt-Smart-Hubspace-Outdoor-Single-Outlet-Wi-Fi-Bluetooth-Plug-HPPA51CWB/316341409
        # https://www.homedepot.com/p/Defiant-15-Amp-120-Volt-Smart-Hubspace-Wi-Fi-Bluetooth-Plug-with-1-Outlet-HPPA11AWB/315636834
        if (
            self._model == "HPPA51CWB"
            or self._model == "HPPA11AWBA023"
            or self._model == "HPSA11CWB"
            or self._model == "HPPA11CWB"
        ):
            self._supported_color_modes.extend([ColorMode.ONOFF])
        # https://www.homedepot.com/p/EcoSmart-16-ft-Smart-Hubspace-RGB-and-Tunable-White-Tape-Light-Works-with-Amazon-Alexa-and-Google-Assistant-AL-TP-RGBCW-60/314680856
        if (
            self._model == "AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232"
            or self._model == "HPKA315CWB"
            or self._model == "HPPA52CWBA023"
        ):
            self._usePowerFunctionInstance = "primary"
            self._supported_color_modes.extend([ColorMode.RGB, ColorMode.WHITE])

        # https://www.homedepot.com/p/Commercial-Electric-4-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538551010/314199717
        # https://www.homedepot.com/p/Commercial-Electric-6-in-Smart-Hubspace-Ultra-Slim-New-Construction-and-Remodel-RGB-W-LED-Recessed-Kit-Works-with-Amazon-Alexa-and-Google-50292/313556988
        #  https://www.homedepot.com/p/EcoSmart-120-Watt-Equivalent-Smart-Hubspace-PAR38-Color-Changing-CEC-LED-Light-Bulb-with-Voice-Control-1-Bulb-11PR38120RGBWH1/318411934
        # https://www.homedepot.com/p/EcoSmart-60-Watt-Equivalent-Smart-Hubspace-A19-Color-Changing-CEC-LED-Light-Bulb-with-Voice-Control-1-Bulb-11A19060WRGBWH1/318411935
        if (
            self._model == "50291, 50292"
            or self._model == "11PR38120RGBWH1"
            or self._model == "11A21100WRGBWH1"
            or self._model == "11A19060WRGBWH1"
        ):
            self._supported_color_modes.extend(
                [ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE]
            )
            self._max_mireds = 454
            self._min_mireds = 154

        # fan
        if self._model == "52133, 37833" or self._model == "76278, 37278" or self._model == "" or self._model == "DriskolFan":
            self._usePowerFunctionInstance = "light-power"
            self._supported_color_modes.extend([ColorMode.BRIGHTNESS])
            self._temperature_suffix = "K"
            self._temperature_choices = []
            for function in functions:
                if function.get("functionClass") == "color-temperature":
                    for value in function.get("values"):
                        temperatureName = value.get("name")
                        if isinstance(
                            temperatureName, str
                        ) and temperatureName.endswith(self._temperature_suffix):
                            try:
                                temperatureValue = int(
                                    temperatureName[: -len(self._temperature_suffix)]
                                )
                            except ValueError:
                                _LOGGER.debug(
                                    f"Can't convert temperatureName {temperatureName} to int"
                                )
                                temperatureValue = None
                            if (
                                temperatureValue is not None
                                and temperatureValue not in self._temperature_choices
                            ):
                                self._temperature_choices.append(temperatureValue)
            if len(self._temperature_choices):
                self._supported_color_modes.extend(
                    [ColorMode.COLOR_TEMP, ColorMode.WHITE]
                )
                self._max_mireds = 1000000 // min(self._temperature_choices) + 1
                self._min_mireds = 1000000 // max(self._temperature_choices)
            else:
                self._temperature_choices = None

        # https://www.homedepot.com/p/Commercial-Electric-5-in-6-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538561010/314254248
        if self._model == "538551010, 538561010, 538552010, 538562010" or self._model == "G19226" or self._model == "HB-10521-HS" or self._model == "17122-HS-WT":
            self._supported_color_modes.extend(
                [ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE]
            )
            self._max_mireds = 370
            self._min_mireds = 154
        # https://www.homedepot.com/p/Hampton-Bay-Lakeshore-13-in-Matte-Black-Smart-Hubspace-CCT-and-RGB-Selectable-LED-Flush-Mount-SMACADER-MAGB01/317216753
        if (
            self._model
            == "SMACADER-MAGD01, SMACADER-MAGB01, SMACADER-MAGW01, CAD1aERMAGW26, CAD1aERMAGP26, CAD1aERMAGA26"
        ):
            self._supported_color_modes.extend(
                [ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE]
            )
            self._max_mireds = 370
            self._min_mireds = 154

        # If model not found, use On/Off Only as a failsafe
        if not self._supported_color_modes:
            self._supported_color_modes.extend([ColorMode.ONOFF])

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
    def color_temp(self) -> int | None:
        """Return the CT color value in mireds."""
        return _convert_color_temp(self._color_temp)

    @property
    def min_mireds(self) -> int or None:
        """Return the coldest color_temp that this light supports."""
        return self._min_mireds

    @property
    def max_mireds(self) -> int or None:
        """Return the warmest color_temp that this light supports."""
        return self._max_mireds

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == "on"

    def send_command(self, field_name, field_state, functionInstance=None) -> None:
        self._hs.setState(self._childId, field_name, field_state, functionInstance)

    def set_send_state(self, field_name, field_state) -> None:
        self._hs.setState(self._childId, field_name, field_state)

    def turn_on(self, **kwargs: Any) -> None:
        state = self._hs.setPowerState(
            self._childId, "on", self._usePowerFunctionInstance
        )

        if ATTR_BRIGHTNESS in kwargs and (
            ColorMode.ONOFF not in self._supported_color_modes
        ):
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            self._hs.setState(
                self._childId, "brightness", _brightness_to_hubspace(brightness)
            )

        if ATTR_RGB_COLOR in kwargs and any(
            mode in COLOR_MODES_COLOR for mode in self._supported_color_modes
        ):
            self._hs.setRGB(self._childId, *kwargs[ATTR_RGB_COLOR])

        if ATTR_WHITE in kwargs and (
            any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes)
            or ColorMode.COLOR_TEMP in self._supported_color_modes
        ):
            self._colorMode = ATTR_WHITE
            self._hs.setState(self._childId, "color-mode", self._colorMode)
            brightness = kwargs.get(ATTR_WHITE, self._brightness)
            self._hs.setState(
                self._childId, "brightness", _brightness_to_hubspace(brightness)
            )

        if ATTR_COLOR_TEMP in kwargs and (
            any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes)
            or ColorMode.COLOR_TEMP in self._supported_color_modes
        ):
            self._color_temp = _convert_color_temp(kwargs[ATTR_COLOR_TEMP])
            if self._temperature_choices is not None:
                self._color_temp = self._temperature_choices[
                    min(
                        range(len(self._temperature_choices)),
                        key=lambda i: abs(
                            self._temperature_choices[i] - self._color_temp
                        ),
                    )
                ]
            if self._temperature_suffix is not None:
                self._hs.setState(
                    self._childId,
                    "color-temperature",
                    str(self._color_temp) + self._temperature_suffix,
                )
            else:
                self._hs.setState(self._childId, "color-temperature", self._color_temp)

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
        state = self._hs.setPowerState(
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
        self._state = self._hs.getPowerState(self._childId)

        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)

        # ColorMode.ONOFF is the only color mode that doesn't support brightness
        if ColorMode.ONOFF not in self._supported_color_modes:
            self._brightness = _brightness_to_hass(
                self._hs.getState(self._childId, "brightness")
            )

        if any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes):
            self._rgbColor = self._hs.getRGB(self._childId)

        if (
            any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes)
            or ColorMode.COLOR_TEMP in self._supported_color_modes
        ):
            self._colorMode = self._hs.getState(self._childId, "color-mode")
            self._color_temp = self._hs.getState(self._childId, "color-temperature")
            if (
                self._temperature_suffix is not None
                and isinstance(self._color_temp, str)
                and self._color_temp.endswith(self._temperature_suffix)
            ):
                self._color_temp = self._color_temp[: -len(self._temperature_suffix)]


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
        return self._state == "on"

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId, "power", "fan-power", "on")

        # Homeassistant uses 0-255
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        brightnessPercent = _brightness_to_hubspace(brightness)
        if self._model != "DriskolFan":
            if brightnessPercent < 30:
                speed = "025"
            elif brightnessPercent < 60:
                speed = "050"
            elif brightnessPercent < 85:
                speed = "075"
            else:
                speed = "100"
            speedstring = "fan-speed-" + speed
        else:
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
        elif fanspeed == "fan-speed-5-60":
            brightness = 153
        elif fanspeed == "fan-speed-5-80":
            brightness = 204    
        elif fanspeed == "fan-speed-100":
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
