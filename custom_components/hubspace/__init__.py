"""Hubspace Fan integration."""

import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import hubspace

DOMAIN = "hubspace"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            },
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.

    hubspace_config = config.get(DOMAIN, {})
    username = hubspace_config[CONF_USERNAME]
    password = hubspace_config[CONF_PASSWORD]

    refresh_token = hubspace.get_refresh_token(username, password)
    auth_token = hubspace.get_auth_token(refresh_token)
    account_id = hubspace.get_account_id(auth_token)
    children = hubspace.get_children(auth_token, account_id)

    hass.data[DOMAIN] = {
        "refresh_token": refresh_token,
        "account_id": account_id,
        "children": children,
    }

    hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)
    hass.helpers.discovery.load_platform("fan", DOMAIN, {}, config)
    return True
