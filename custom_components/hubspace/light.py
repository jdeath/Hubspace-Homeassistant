"""Platform for light integration."""
from __future__ import annotations

import logging

from .hubspace import HubSpace
import voluptuous as vol

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_RGB_COLOR, PLATFORM_SCHEMA, COLOR_MODE_BRIGHTNESS, COLOR_MODE_COLOR_TEMP, COLOR_MODE_RGB, COLOR_MODE_ONOFF, LightEntity)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import timedelta

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
    hs = HubSpace(username,password)
    
    entities = []
    for friendlyname in config.get(CONF_FRIENDLYNAMES): 
    
        _LOGGER.debug("freindlyname " + friendlyname )
        [childId, model, deviceId] = hs.getChildId(friendlyname)
        
        _LOGGER.debug("Switch on Model " + model )
        _LOGGER.debug("childId: " + childId )
        _LOGGER.debug("deviceId: " + deviceId )
        
        if model == 'HPKA315CWB':
            _LOGGER.debug("Creating Outlets" )
            entities.append(HubspaceOutlet(hs, friendlyname,"1",debug))
            entities.append(HubspaceOutlet(hs, friendlyname,"2",debug))
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
        self._useBrightness = False
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None
        
        # colorMode == 'color' || 'white' 
        self._useColorOrWhite = False
        self._colorMode = None
        self._whiteTemp = None
        self._rgbColor = None
        
        [self._childId, self._model, self._deviceId] = self._hs.getChildId(self._name)
        
        # https://www.homedepot.com/p/Commercial-Electric-500-Watt-Single-Pole-Smart-Hubspace-Dimmer-with-Motion-Sensor-White-HPDA311CWB/317249353
        if self._model == 'HPDA311CWB':
            self._useBrightness = True
        
        #https://www.homedepot.com/p/EcoSmart-16-ft-Smart-Hubspace-RGB-and-Tunable-White-Tape-Light-Works-with-Amazon-Alexa-and-Google-Assistant-AL-TP-RGBCW-60/314680856
        if self._model == 'AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232' or self._model == 'HPKA315CWB' or self._model == '52133, 37833':
            self._usePrimaryFunctionInstance = True
        
        # https://www.homedepot.com/p/Commercial-Electric-4-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538551010/314199717
        # https://www.homedepot.com/p/Commercial-Electric-6-in-Smart-Hubspace-Ultra-Slim-New-Construction-and-Remodel-RGB-W-LED-Recessed-Kit-Works-with-Amazon-Alexa-and-Google-50292/313556988
        if self._model == '50291, 50292':
            self._useColorOrWhite = True    
        
        # https://www.homedepot.com/p/Commercial-Electric-5-in-6-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538561010/314254248
        if self._model == '538551010, 538561010, 538552010, 538562010':
            self._useColorOrWhite = True
            self._useBrightness = True
        
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId  

    @property
    def supported_color_modes(self) -> set[str] or None:
        """Flag supported color modes."""
        if self._useBrightness:
            return {COLOR_MODE_BRIGHTNESS}
        elif self._useColorOrWhite:
            return {COLOR_MODE_RGB}
        else:
            return {COLOR_MODE_ONOFF}
    
    @property
    def brightness(self) -> int or None:
        """Return the brightness of this light between 0..255."""
        return self._brightness
    
    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        state = self._hs.setPowerState(self._childId,"on",self._usePrimaryFunctionInstance)
        if self._useBrightness:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            self._hs.setState(self._childId,"brightness",_brightness_to_hubspace(brightness))
        
        if self._useColorOrWhite and ATTR_RGB_COLOR in kwargs:
            self._hs.setRGB(self._childId,*kwargs[ATTR_RGB_COLOR])
    
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
        state = self._hs.setPowerState(self._childId,"off",self._usePrimaryFunctionInstance)
        
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
            
        if self._useBrightness:
            self._brightness = _brightness_to_hass(self._hs.getState(self._childId,"brightness"))
        
        if self._useColorOrWhite:
            self._colorMode = self._hs.getState(self._childId,'color-mode')
            self._rgbColor = self._hs.getRGB(self._childId)

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
        self._useBrightness = False
        self._usePrimaryFunctionInstance = False
        self._hs = hs
        self._deviceId = None
        self._debugInfo = None
        self._outletIndex = outletIndex
        
        [self._childId, self._model, self._deviceId] = self._hs.getChildId(friendlyname)
    
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._deviceId + "_" + self._outletIndex 

    @property
    def supported_color_modes(self) -> set[str] or None:
        """Flag supported color modes."""
        return {COLOR_MODE_ONOFF}
    
    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId,'toggle',"outlet-" + self._outletIndex ,'on')
     
    
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
        