"""Platform for fan integration."""
import string
from typing import Any
from .const import FunctionClass, FunctionInstance
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from . import DOMAIN, hubspace
from homeassistant.components.fan import FanEntity


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType or None = None,
) -> None:
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.

    domain_data = hass.data[DOMAIN]
    fans = [
        HubspaceFanEntity(
            child, domain_data["account_id"], domain_data["refresh_token"]
        )
        for child in domain_data["children"]
        if child.get("semanticDescriptionKey", None) == "fan"
    ]
    add_entities(fans, True)


class HubspaceFanFunction(hubspace.HubspaceFunction):
    @property
    def values(self) -> list[Any]:
        if not self._values:
            self._values = [value["name"] for value in self._data["values"]].sort(
                key=self._value_key
            )
        return self._values

    def _value_key(self, value: Any) -> Any:
        if self.function_key == (FunctionClass.FAN_SPEED, FunctionInstance.FAN_SPEED):
            return int(str(value).strip(string.ascii_letters))
        return value


class HubspaceFanEntity(FanEntity, hubspace.HubspaceEntity):
    """Representation of a Hubspace Fan."""

    _function_class = HubspaceFanFunction

    @property
    def is_on(self) -> bool or None:
        """Return whether the fan is on."""
        return self._get_state_value(FunctionClass.POWER, FunctionInstance.FAN_POWER)

    def turn_on(
        self,
        percentage: int or None = None,
        preset_mode: str or None = None,
        **kwargs,
    ) -> None:
        """Instruct the light to turn on."""
        self.set_state(
            [
                {
                    "functionClass": FunctionClass.POWER.value,
                    "functionInstance": FunctionInstance.FAN_POWER.value,
                    "value": STATE_ON,
                },
            ]
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self.set_state(
            [
                {
                    "functionClass": FunctionClass.POWER.value,
                    "functionInstance": FunctionInstance.FAN_POWER.value,
                    "value": STATE_OFF,
                },
            ]
        )
