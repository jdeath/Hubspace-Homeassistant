"""Platform for light integration."""
from __future__ import annotations

import logging

from . import hubspace as hs
import voluptuous as vol

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA,
                                            LightEntity)
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

        self._refresh_token = hs.getRefreshCode(self._username,self._password)
        self._accountId = hs.getAccountId(self._refresh_token)
        self._childId = hs.getChildId(self._refresh_token,self._accountId,self._name)

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        state = hs.setPowerState(self._refresh_token,self._accountId,self._childId,"on")
        

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
