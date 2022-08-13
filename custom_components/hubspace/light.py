"""Platform for light integration."""
from __future__ import annotations

import logging

from .hubspace import HubSpace
import voluptuous as vol

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_WHITE, ATTR_COLOR_TEMP, PLATFORM_SCHEMA, ColorMode, COLOR_MODES_COLOR, LightEntity)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import timedelta

# Import exceptions from the requests module
import requests.exceptions

SCAN_INTERVAL = timedelta(seconds=60)
BASE_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_DEBUG: Final = "debug"

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_DEBUG, default=False): cv.boolean,
    vol.Required(CONF_FRIENDLYNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
})

def _brightness_to_hass(value):
        return int(value) * 255 // 100


def _brightness_to_hubspace(value):
        return value * 100 // 255

def _convert_color_temp(value):
        return 1000000 // int(value)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    
    username = config[CONF_USERNAME]
    password = config.get(CONF_PASSWORD)
    debug = config.get(CONF_DEBUG)
    try:
        hs = HubSpace(username,password)
    except requests.exceptions.ReadTimeout as ex:
        raise PlatformNotReady(f"Connection error while connecting to hubspace: {ex}") from ex
    
    entities = []
    for friendlyname in config.get(CONF_FRIENDLYNAMES): 

        _LOGGER.debug("friendlyname " + friendlyname )
        [childId, model, deviceId,deviceClass] = hs.getChildId(friendlyname)

        _LOGGER.debug("Switch on Model " + model )
        _LOGGER.debug("childId: " + childId )
        _LOGGER.debug("deviceId: " + deviceId )
        _LOGGER.debug("deviceClass: " + deviceClass )
        
        if model == 'HPKA315CWB':
            _LOGGER.debug("Creating Outlets" )
            entities.append(HubspaceOutlet(hs, friendlyname,"1",debug))
            entities.append(HubspaceOutlet(hs, friendlyname,"2",debug))
        elif model == 'HB-200-1215WIFIB':
            _LOGGER.debug("Creating Transformers" )
            entities.append(HubspaceTransformer(hs, friendlyname,"1",debug))
            entities.append(HubspaceTransformer(hs, friendlyname,"2",debug))
            entities.append(HubspaceTransformer(hs, friendlyname,"3",debug))
        elif model == '52133, 37833':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyname,debug))
            _LOGGER.debug("Creating Light" )
            entities.append(HubspaceLight(hs, friendlyname,debug))
        elif model == '76278, 37278':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyname,debug))
            _LOGGER.debug("Creating Light" )
            entities.append(HubspaceLight(hs, friendlyname,debug))    
        else:
            _LOGGER.debug("creating lights" )
            entities.append(HubspaceLight(hs, friendlyname,debug))
    
    if not entities:
        return
    add_entities(entities, True)
    # Setup connection with devices/cloud
    

class HubspaceLight(LightEntity):
    """Representation of an Awesome Light."""
    
    
    
    def __init__(self, hs, friendlyname,debug) -> None:
        """Initialize an AwesomeLight."""
        
        self._name = friendlyname

        
        self._debug = debug
        self._state = 'off'
        self._childId = None
        self._model = None
        self._brightness = None
        self._usePowerFunctionInstance = None
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None

        # colorMode == 'color' || 'white' 
        self._colorMode = None
        self._colorTemp = None
        self._min_mireds = None
        self._max_mireds = None
        self._rgbColor = None
        deviceClass = None
        [self._childId, self._model, self._deviceId,deviceClass] = self._hs.getChildId(self._name)

        self._supported_color_modes = []

        # https://www.homedepot.com/p/Commercial-Electric-500-Watt-Single-Pole-Smart-Hubspace-Dimmer-with-Motion-Sensor-White-HPDA311CWB/317249353
        if self._model == 'HPDA311CWB':
            self._supported_color_modes.extend([ColorMode.BRIGHTNESS])

        #https://www.homedepot.com/p/EcoSmart-16-ft-Smart-Hubspace-RGB-and-Tunable-White-Tape-Light-Works-with-Amazon-Alexa-and-Google-Assistant-AL-TP-RGBCW-60/314680856
        if self._model == 'AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232' or self._model == 'HPKA315CWB':
            self._usePowerFunctionInstance = 'primary'
        
        # https://www.homedepot.com/p/Commercial-Electric-4-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538551010/314199717
        # https://www.homedepot.com/p/Commercial-Electric-6-in-Smart-Hubspace-Ultra-Slim-New-Construction-and-Remodel-RGB-W-LED-Recessed-Kit-Works-with-Amazon-Alexa-and-Google-50292/313556988
        if self._model == '50291, 50292':
            self._supported_color_modes.extend([ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE])
        
        #fan
        if self._model == '52133, 37833' or self._model == '76278, 37278':
            self._usePowerFunctionInstance = 'light-power'
            self._supported_color_modes.extend([ColorMode.BRIGHTNESS])

        # https://www.homedepot.com/p/Commercial-Electric-5-in-6-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538561010/314254248
        if self._model == '538551010, 538561010, 538552010, 538562010':
            self._supported_color_modes.extend([ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE])

        # https://www.homedepot.com/p/Hampton-Bay-Lakeshore-13-in-Matte-Black-Smart-Hubspace-CCT-and-RGB-Selectable-LED-Flush-Mount-SMACADER-MAGB01/317216753
        if self._model == 'SMACADER-MAGD01, SMACADER-MAGB01, SMACADER-MAGW01, CAD1aERMAGW26, CAD1aERMAGP26, CAD1aERMAGA26':
            self._supported_color_modes.extend([ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE])
            self._max_mireds = 370
            self._min_mireds = 154


    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId

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
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        state = self._hs.setPowerState(self._childId,"on",self._usePowerFunctionInstance)

        if ATTR_BRIGHTNESS in kwargs and (ColorMode.ONOFF not in self._supported_color_modes):
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            self._hs.setState(self._childId,"brightness",_brightness_to_hubspace(brightness))

        if ATTR_RGB_COLOR in kwargs and any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes):
            self._hs.setRGB(self._childId,*kwargs[ATTR_RGB_COLOR])

        if ATTR_WHITE in kwargs and (any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes) or ColorMode.COLOR_TEMP in self._supported_color_modes):
            self._colorMode = ATTR_WHITE
            self._hs.setState(self._childId,"color-mode",self._colorMode)
            brightness = kwargs.get(ATTR_WHITE, self._brightness)
            self._hs.setState(self._childId,"brightness",_brightness_to_hubspace(brightness))

        if ATTR_COLOR_TEMP in kwargs and (any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes) or ColorMode.COLOR_TEMP in self._supported_color_modes):
            self._color_temp = _convert_color_temp(kwargs[ATTR_COLOR_TEMP])
            self._hs.setState(self._childId,"color-temperature",self._color_temp)

    @property
    def rgb_color(self):
        """Return the rgb value."""
        return self._rgbColor
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"]= self._model
        attr["deviceId"] = self._deviceId
        attr["devbranch"] = False
        
        attr["debugInfo"] = self._debugInfo
        
        return attr
        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        state = self._hs.setPowerState(self._childId,"off",self._usePowerFunctionInstance)
        
    @property
    def should_poll(self):
        """Turn on polling """
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
            self._brightness = _brightness_to_hass(self._hs.getState(self._childId,"brightness"))

        if any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes):
            self._rgbColor = self._hs.getRGB(self._childId)

        if any(mode in COLOR_MODES_COLOR for mode in self._supported_color_modes) or ColorMode.COLOR_TEMP in self._supported_color_modes:
            self._colorMode = self._hs.getState(self._childId,'color-mode')
            self._color_temp = self._hs.getState(self._childId,'color-temperature')

class HubspaceOutlet(LightEntity):
    """Representation of an Awesome Light."""
    
    
    
    def __init__(self, hs, friendlyname,outletIndex,debug) -> None:
        """Initialize an AwesomeLight."""
        
        self._name = friendlyname + "_outlet_" + outletIndex 
        
        self._debug = debug
        self._state = 'off'
        self._childId = None
        self._model = None
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None
        self._outletIndex = outletIndex
        deviceClass = None
        [self._childId, self._model, self._deviceId,deviceClass] = self._hs.getChildId(friendlyname)
    
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId + "_" + self._outletIndex 

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
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId,'toggle',"outlet-" + self._outletIndex ,'on')
        self.update()
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"]= self._model
        attr["deviceId"] = self._deviceId + "_" + self._outletIndex
        attr["devbranch"] = False
        
        attr["debugInfo"] = self._debugInfo
        
        return attr
        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(self._childId,'toggle',"outlet-" + self._outletIndex ,'off')
        self.update()
        
    @property
    def should_poll(self):
        """Turn on polling """
        return True
        
    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(self._childId,'toggle',"outlet-" + self._outletIndex)
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)

class HubspaceFan(LightEntity):
    """Representation of an Awesome Light."""
    
        
    def __init__(self, hs, friendlyname, debug) -> None:
        """Initialize an AwesomeLight."""
        
        self._name = friendlyname + "_fan" 
        
        self._debug = debug
        self._state = 'off'
        self._childId = None
        self._model = None
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None
        
        deviceClass = None
        [self._childId, self._model, self._deviceId,deviceClass] = self._hs.getChildId(friendlyname)
    
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId + "_fan" 

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId,'power','fan-power','on')
        
        # Homeassistant uses 0-255
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        brightnessPercent = _brightness_to_hubspace(brightness)
        if brightnessPercent < 30:
            speed = '025'
        elif brightnessPercent < 60:
            speed = '050'
        elif brightnessPercent < 85:
            speed = '075'
        else:
            speed = '100'
        speedstring = 'fan-speed-' + speed
        
        self._hs.setStateInstance(self._childId,'fan-speed','fan-speed',speedstring)

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
        attr["model"]= self._model
        attr["deviceId"] = self._deviceId + "_fan"
        attr["devbranch"] = False
        
        attr["debugInfo"] = self._debugInfo
        
        return attr
        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(self._childId,'power','fan-power','off')
        self._hs.setStateInstance(self._childId,'fan-speed','fan-speed','fan-speed-000')
        
    @property
    def should_poll(self):
        """Turn on polling """
        return True
        
    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(self._childId,'power','fan-power')
        fanspeed = self._hs.getStateInstance(self._childId,'fan-speed','fan-speed')
        brightness = 0
        
        if fanspeed == 'fan-speed-000':
            brightness = 0
        elif fanspeed == 'fan-speed-025':
            brightness = 63
        elif fanspeed == 'fan-speed-050':
            brightness = 127
        elif fanspeed == 'fan-speed-075':
            brightness = 191
        elif fanspeed == 'fan-speed-100':
            brightness = 255
        self._brightness = brightness
            
        
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)

class HubspaceTransformer(LightEntity):
    """Representation of an Awesome Light."""
    
    
    
    def __init__(self, hs, friendlyname,outletIndex,debug) -> None:
        """Initialize an AwesomeLight."""
        
        self._name = friendlyname + "_transformer_" + outletIndex 
        
        self._debug = debug
        self._state = 'off'
        self._childId = None
        self._model = None
        self._brightness = None
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None
        self._watts = None
        self._volts = None
        
        self._outletIndex = outletIndex
        deviceClass = None
        [self._childId, self._model, self._deviceId,deviceClass] = self._hs.getChildId(friendlyname)
    
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId + "_" + self._outletIndex 

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
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId,'toggle',"zone-" + self._outletIndex ,'on')
        self.update()
        
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"]= self._model
        attr["deviceId"] = self._deviceId + "_" + self._outletIndex
        attr["devbranch"] = False
        attr["watts"] = self._watts
        attr["volts"] = self._volts
        
        attr["debugInfo"] = self._debugInfo
        
        return attr
        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._hs.setStateInstance(self._childId,'toggle',"zone-" + self._outletIndex ,'off')
        self.update()
        
    @property
    def should_poll(self):
        """Turn on polling """
        return True
        
    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(self._childId,'toggle',"zone-" + self._outletIndex)
        
        if self._outletIndex == '1':
            self._watts = self._hs.getState(self._childId,'watts')
            self._volts = self._hs.getState(self._childId,'output-voltage-switch')
            
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)