"""Home Assistant entity for interacting with Afero climate."""

from functools import partial

from aioafero.v1 import AferoBridgeV1
from aioafero.v1.controllers.event import EventType
from aioafero.v1.controllers.thermostat import ThermostatController
from aioafero.v1.models import Thermostat
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    FAN_OFF,
    FAN_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator


class HubspaceThermostat(HubspaceBaseEntity, ClimateEntity):
    """Representation of an Afero climate."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: ThermostatController,
        resource: Thermostat,
    ) -> None:
        """Initialize an Afero Climate."""

        super().__init__(bridge, controller, resource)
        self._supported_fan: list[str] = []
        self._supported_hvac_modes: list[HVACMode]
        self._supported_features: ClimateEntityFeature = ClimateEntityFeature(0)
        if self.resource.target_temperature:
            self._supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self.resource.supports_fan_mode:
            self._supported_features |= ClimateEntityFeature.FAN_MODE
        if self.resource.supports_temperature_range:
            self._supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {}

    @property
    def current_temperature(self) -> float | None:
        """Returns the current temperature."""
        return self.resource.current_temperature

    @property
    def fan_mode(self) -> str | None:
        """Returns the currently selected fan mode."""
        if self.resource.fan_mode.mode == "on":
            return FAN_ON
        if self.resource.fan_mode.mode == "off":
            return FAN_OFF
        return self.resource.fan_mode.mode

    @property
    def fan_modes(self) -> list[str] | None:
        """Returns all available fan modes."""
        return list(self.resource.fan_mode.modes)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Returns the current state of hvac operation."""
        mapping = {
            "cooling": HVACAction.COOLING,
            "heating": HVACAction.HEATING,
            "off": HVACAction.OFF,
        }
        mapped = mapping.get(self.resource.hvac_action)
        if mapped:
            return mapped
        if self.resource.hvac_mode.mode == "fan":
            return HVACAction.FAN
        return self.resource.hvac_action

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Returns the current hvac mode."""
        mapping = {
            "cool": HVACMode.COOL,
            "heat": HVACMode.HEAT,
            "fan": HVACMode.FAN_ONLY,
            "off": HVACMode.OFF,
            "auto": HVACMode.HEAT_COOL,
        }
        mapped = mapping.get(self.resource.hvac_mode.mode)
        if not mapped:
            self.logger.warning("Unknown hvac mode: %s", self.resource.hvac_mode.mode)
            return None
        return mapped

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Returns all available hvac modes."""
        mapping = {
            "cool": HVACMode.COOL,
            "heat": HVACMode.HEAT,
            "fan": HVACMode.FAN_ONLY,
            "off": HVACMode.OFF,
            "auto": HVACMode.HEAT_COOL,
        }
        return [
            val
            for key, val in mapping.items()
            if key in self.resource.hvac_mode.supported_modes
        ]

    @property
    def max_temp(self) -> float | None:
        """Returns the maximum allowed temperature for the current mode."""
        return self.resource.target_temperature_max

    @property
    def min_temp(self) -> float | None:
        """Returns the minimum allowed temperature for the current mode."""
        return self.resource.target_temperature_min

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Returns all supported features for the climate entity."""
        return self._supported_features

    @property
    def target_temperature(self) -> float | None:
        """Returns the temperature that we are trying to reach."""
        return self.resource.target_temperature

    @property
    def target_temperature_high(self) -> float | None:
        """Returns the upper bound (cool) temperature when set to auto."""
        return self.resource.target_temperature_range[1]

    @property
    def target_temperature_low(self) -> float | None:
        """Returns the lower bound (heat) temperature when set to auto."""
        return self.resource.target_temperature_range[0]

    @property
    def target_temperature_step(self) -> float | None:
        """Returns the amount the thermostat can increment."""
        return self.resource.target_temperature_step

    @property
    def temperature_unit(self) -> str:
        """Unit for backend data."""
        # Hubspace always returns in C
        return UnitOfTemperature.CELSIUS

    @update_decorator
    async def translate_hvac_mode_to_hubspace(self, hvac_mode) -> str | None:
        """Convert HomeAssistant -> Hubspace."""
        tracked_modes = {
            HVACMode.OFF: "off",
            HVACMode.HEAT: "heat",
            HVACMode.COOL: "cool",
            HVACMode.FAN_ONLY: "fan",
            HVACMode.HEAT_COOL: "auto",
        }
        return tracked_modes.get(hvac_mode)

    @update_decorator
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new hvac mode."""
        mode = await self.translate_hvac_mode_to_hubspace(hvac_mode)
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, hvac_mode=mode
        )

    @update_decorator
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        tracked_modes = {
            FAN_ON: "on",
        }
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            fan_mode=tracked_modes.get(fan_mode, fan_mode),
        )

    @update_decorator
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            target_temperature=kwargs.get(ATTR_TEMPERATURE),
            target_temperature_auto_cooling=kwargs.get(ATTR_TARGET_TEMP_HIGH),
            target_temperature_auto_heating=kwargs.get(ATTR_TARGET_TEMP_LOW),
            hvac_mode=await self.translate_hvac_mode_to_hubspace(
                kwargs.get(ATTR_HVAC_MODE)
            ),
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: ThermostatController = api.thermostats
    make_entity = partial(HubspaceThermostat, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Thermostat) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
