"""Platform for light integration."""
from __future__ import annotations

import logging

from . import hubspace as hs
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

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
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
    
    entities = [HubspaceLight(username, password, friendlyname) for friendlyname in config.get(CONF_FRIENDLYNAMES)]
    if not entities:
        return
    add_entities(entities, True)
    # Setup connection with devices/cloud
    

class HubspaceLight(LightEntity):
    """Representation of an Awesome Light."""
    
    
    
    def __init__(self, username, password, friendlyname) -> None:
        """Initialize an AwesomeLight."""
        self._username = username
        self._password = password
        self._name = friendlyname
        self._refresh_token = None
        self._accountId = None
        self._state = 'off'
        self._childId = None
        self._model = None
        self._brightness = None
        self._useBrightness = False
        
        # colorMode == 'color' || 'white' 
        self._useColorOrWhite = False
        self._colorMode = None
        self._whiteTemp = None
        self._rgbColor = None
        
        self._refresh_token = hs.getRefreshCode(self._username,self._password)
        self._accountId = hs.getAccountId(self._refresh_token)
        [self._childId, self._model] = hs.getChildId(self._refresh_token,self._accountId,self._name)
        
        # https://www.homedepot.com/p/Commercial-Electric-500-Watt-Single-Pole-Smart-Hubspace-Dimmer-with-Motion-Sensor-White-HPDA311CWB/317249353
        if self._model == 'HPDA311CWB':
            self._useBrightness = True
            
        # https://www.homedepot.com/p/Commercial-Electric-4-in-Smart-Hubspace-Color-Selectable-CCT-Integrated-LED-Recessed-Light-Trim-Works-with-Amazon-Alexa-and-Google-538551010/314199717
        # https://www.homedepot.com/p/Commercial-Electric-6-in-Smart-Hubspace-Ultra-Slim-New-Construction-and-Remodel-RGB-W-LED-Recessed-Kit-Works-with-Amazon-Alexa-and-Google-50292/313556988
        if self._model == '50291' or self._model == '50292' or self._model == '50291, 50292':
            self._useColorOrWhite = True    
            
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

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
        state = hs.setPowerState(self._refresh_token,self._accountId,self._childId,"on")
        if self._useBrightness:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
            hs.setState(self._refresh_token,self._accountId,self._childId,"brightness",_brightness_to_hubspace(brightness))
        
        if self._useColorOrWhite and ATTR_RGB_COLOR in kwargs:
            hs.setRGB(self._refresh_token,self._accountId,self._childId,*kwargs[ATTR_RGB_COLOR])
    
    @property
    def rgb_color(self):
        """Return the rgb value."""
        return self._rgbColor
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["model"]= self._model
        return attr
        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        state = hs.setPowerState(self._refresh_token,self._accountId,self._childId,"off")
        
    @property
    def should_poll(self):
        """Turn on polling """
        return True
        
    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = hs.getPowerState(self._refresh_token,self._accountId,self._childId)
        
        if self._useBrightness:
            self._brightness = _brightness_to_hass(hs.getState(self._refresh_token,self._accountId,self._childId,"brightness"))
        
        if self._useColorOrWhite:
            self._colorMode = hs.getState(self._refresh_token,self._accountId,self._childId,'color-mode')
            self._rgbColor = hs.getRGB(self._refresh_token,self._accountId,self._childId)