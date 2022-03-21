"""Platform for light integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    COLOR_MODE_BRIGHTNESS,
    LightEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

# Import the device class from the component that you want to support
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, hubspace

SCAN_INTERVAL = timedelta(seconds=30)
BASE_INTERVAL = timedelta(seconds=30)


def _brightness_to_hass(value):
    return int(value) * 255 // 100


def _brightness_to_hubspace(value):
    return value * 100 // 255


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.

    domain_data = hass.data[DOMAIN]
    lights = [
        HubspaceLight(domain_data["refresh_token"], domain_data["account_id"], child)
        for child in domain_data["children"]
        if child.get("semanticDescriptionKey", None) == "light"
    ]
    if not lights:
        return
    add_entities(lights, True)


class HubspaceLight(LightEntity):
    """Representation of a Hubspace Light."""

    _skip_update: bool = False

    def __init__(self, refresh_token, account_id, light) -> None:
        """Initialize a HubspaceLight."""
        self._attr_unique_id = light.get("id", None)
        self._name = light.get("friendlyName", None)
        self._refresh_token = refresh_token
        self._account_id = account_id
        self._attr_supported_color_modes = [COLOR_MODE_BRIGHTNESS]
        self._state = hubspace.parse_state(
            light.get("state", {}),
            function_class="power",
            function_instance="light-power",
            default_value=STATE_OFF,
        )
        self._attr_brightness = hubspace.parse_state(
            light.get("state", {}),
            function_class="brightness",
            default_value=255,
            value_parser=_brightness_to_hass,
        )
        self._skip_update = False

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == STATE_ON

    def turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness)
        state = hubspace.set_state(
            self._refresh_token,
            self._account_id,
            self._attr_unique_id,
            values=[
                {
                    "functionClass": "power",
                    "functionInstance": "light-power",
                    "value": "on",
                },
                {
                    "functionClass": "brightness",
                    "value": _brightness_to_hubspace(brightness),
                },
            ],
        )
        if state is not None:
            self._state = hubspace.parse_state(
                state,
                function_class="power",
                function_instance="light-power",
                default_value=self._state,
            )
            self._attr_brightness = hubspace.parse_state(
                state,
                function_class="brightness",
                default_value=255,
                value_parser=_brightness_to_hass,
            )
            self._skip_update = True

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        state = hubspace.set_state(
            self._refresh_token,
            self._account_id,
            self._attr_unique_id,
            values=[
                {
                    "functionClass": "power",
                    "functionInstance": "light-power",
                    "value": "off",
                },
            ],
        )
        if state is not None:
            self._state = hubspace.parse_state(
                state,
                function_class="power",
                function_instance="light-power",
                default_value=self._state,
            )
            self._skip_update = True

    @property
    def should_poll(self):
        """Turn on polling"""
        return True

    def update(self) -> None:
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        state = hubspace.get_state(
            self._refresh_token, self._account_id, self._attr_unique_id
        )
        if not self._skip_update:
            self._state = hubspace.parse_state(
                state,
                function_class="power",
                function_instance="light-power",
                default_value=self._state,
            )
            self._attr_brightness = hubspace.parse_state(
                state,
                function_class="brightness",
                default_value=255,
                value_parser=_brightness_to_hass,
            )
        self._skip_update = False
