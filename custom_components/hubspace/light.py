from functools import partial

from aioafero import EventType
from aioafero.v1 import AferoBridgeV1, LightController
from aioafero.v1.models import Light
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    filter_supported_color_modes,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator


class HubspaceLight(HubspaceBaseEntity, LightEntity):
    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: LightController,
        resource: Light,
    ) -> None:
        super().__init__(bridge, controller, resource)
        self._supported_features: LightEntityFeature = LightEntityFeature(0)
        supported_color_modes = {ColorMode.ONOFF}
        if self.resource.supports_color:
            supported_color_modes.add(ColorMode.RGB)
        if self.resource.supports_color_temperature:
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        if self.resource.supports_dimming:
            supported_color_modes.add(ColorMode.BRIGHTNESS)
        self._attr_supported_color_modes = filter_supported_color_modes(
            supported_color_modes
        )

    @property
    def brightness(self) -> int | None:
        return (
            value_to_brightness((1, 100), self.resource.brightness)
            if self.resource.dimming
            else None
        )

    @property
    def color_mode(self) -> ColorMode:
        return get_color_mode(self.resource, self._attr_supported_color_modes)

    @property
    def color_temp_kelvin(self) -> int | None:
        return (
            self.resource.color_temperature.temperature
            if self.resource.color_temperature
            else None
        )

    @property
    def effect(self) -> str | None:
        return (
            self.resource.effect.effect
            if (self.resource.effect and self.resource.color_mode.mode == "sequence")
            else None
        )

    @property
    def effect_list(self) -> list[str] | None:
        all_effects = []
        for effects in self.resource.effect.effects.values() or []:
            all_effects.extend(effects)
        return all_effects or None

    @property
    def is_on(self) -> bool | None:
        return self.resource.is_on

    @property
    def max_color_temp_kelvin(self) -> int | None:
        return (
            max(self.resource.color_temperature.supported)
            if self.resource.color_temperature
            else None
        )

    @property
    def min_color_temp_kelvin(self) -> int | None:
        return (
            min(self.resource.color_temperature.supported)
            if self.resource.color_temperature
            else None
        )

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return (
            (
                self.resource.color.red,
                self.resource.color.green,
                self.resource.color.blue,
            )
            if self.resource.color
            else None
        )

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return self._attr_supported_color_modes

    @property
    def supported_features(self) -> LightEntityFeature:
        if self.resource.effect:
            return LightEntityFeature(0) | LightEntityFeature.EFFECT
        else:
            return LightEntityFeature(0)

    @update_decorator
    async def async_turn_on(self, **kwargs) -> None:
        brightness: int | None = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(brightness_to_value((1, 100), kwargs[ATTR_BRIGHTNESS]))
        temperature: int | None = kwargs.get(ATTR_COLOR_TEMP_KELVIN, None)
        color: tuple[int, int, int] | None = kwargs.get(ATTR_RGB_COLOR, None)
        effect: str | None = kwargs.get(ATTR_EFFECT, None)
        color_mode: str | None = None
        if temperature:
            color_mode = "white"
        elif color:
            color_mode = "color"
        elif effect:
            color_mode = "sequence"
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            brightness=brightness,
            temperature=temperature,
            color=color,
            color_mode=color_mode,
            effect=effect,
        )

    @update_decorator
    async def async_turn_off(self, **kwargs) -> None:
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=False,
        )


def get_color_mode(resource: Light, supported_modes: set[ColorMode]) -> ColorMode:
    """Determine the correct mode

    :param resource: Light from aioafero
    :param supported_modes: Supported color modes
    """
    if not resource.color_mode:
        return list(supported_modes)[0] if len(supported_modes) else ColorMode.ONOFF
    elif resource.color_mode.mode == "color":
        return ColorMode.RGB
    elif resource.color_mode.mode == "white":
        if ColorMode.COLOR_TEMP in supported_modes:
            return ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        else:
            return ColorMode.ONOFF
    else:
        return list(supported_modes)[-1] if len(supported_modes) else ColorMode.ONOFF


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: LightController = api.lights
    make_entity = partial(HubspaceLight, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Light) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
