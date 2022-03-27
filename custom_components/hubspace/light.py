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

from . import DOMAIN
from .const import FunctionClass, FunctionInstance
from .hubspace import HubspaceEntity, HubspaceStateValue

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
        HubspaceLight(child, domain_data["account_id"], domain_data["refresh_token"])
        for child in domain_data["children"]
        if child.get("semanticDescriptionKey", None) == "light"
    ]
    add_entities(lights, True)


class HubspaceLightStateValue(HubspaceStateValue):
    @property
    def value(self) -> Any or None:
        if self.function_class == FunctionClass.BRIGHTNESS:
            return _brightness_to_hass(self._data.get("value"))
        return super().value


class HubspaceLight(LightEntity, HubspaceEntity):
    """Representation of a Hubspace Light."""

    _state_value_class = HubspaceLightStateValue

    @property
    def supported_color_modes(self) -> set[str] or None:
        """Flag supported color modes."""
        return {COLOR_MODE_BRIGHTNESS}

    @property
    def is_on(self) -> bool or None:
        """Return whether the fan is on."""
        return self._get_state_value(FunctionClass.POWER, FunctionInstance.LIGHT_POWER)

    @property
    def brightness(self) -> int or None:
        """Return the brightness of this light between 0..255."""
        return self._get_state_value(FunctionClass.BRIGHTNESS)

    def turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness)
        self.set_state(
            [
                {
                    "functionClass": FunctionClass.POWER.value,
                    "functionInstance": FunctionInstance.LIGHT_POWER.value,
                    "value": STATE_ON,
                },
                {
                    "functionClass": FunctionClass.BRIGHTNESS.value,
                    "value": _brightness_to_hubspace(brightness),
                },
            ]
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self.set_state(
            [
                {
                    "functionClass": FunctionClass.POWER.value,
                    "functionInstance": FunctionInstance.LIGHT_POWER.value,
                    "value": STATE_OFF,
                },
            ]
        )
