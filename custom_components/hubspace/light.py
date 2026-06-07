"""Home Assistant entity for interacting with Afero Light."""

from functools import partial

from aioafero import EventType
from aioafero.v1 import AferoBridgeV1, LightController
from aioafero.v1.models import Light
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_WHITE,
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
from .entity import HubspaceBaseEntity


class HubspaceLight(HubspaceBaseEntity, LightEntity):
    """Representation of an Afero light."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: LightController,
        resource: Light,
    ) -> None:
        """Initialize an Afero light."""

        super().__init__(bridge, controller, resource)
        self._supported_features: LightEntityFeature = LightEntityFeature(0)
        supported_color_modes = {ColorMode.ONOFF}
        if self.resource.supports_color:
            supported_color_modes.add(ColorMode.RGB)
        if self.resource.supports_color_temperature:
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        if is_api_white_zone(self.resource) and self.resource.supports_color:
            # Trim-style zones: API warm white via color-mode white (no CCT slider).
            # HA requires RGB alongside WHITE in supported_color_modes.
            supported_color_modes.add(ColorMode.WHITE)
        if self.resource.supports_dimming:
            supported_color_modes.add(ColorMode.BRIGHTNESS)
        self._attr_supported_color_modes = filter_supported_color_modes(
            supported_color_modes
        )

    @property
    def brightness(self) -> int | None:
        """The brightness of this light between 1..255."""
        if not self.resource.dimming:
            return None
        pct = self.resource.brightness
        if pct is None:
            pct = 100
        return value_to_brightness((1, 100), pct)

    @property
    def color_mode(self) -> ColorMode:
        """Get the current color mode for the light."""
        return get_color_mode(self.resource, self._attr_supported_color_modes)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Get the current color temperature for the light."""
        return (
            self.resource.color_temperature.temperature
            if self.resource.color_temperature
            else None
        )

    @property
    def effect(self) -> str | None:
        """Get the current effect for the light."""
        return (
            self.resource.effect.effect
            if (self.resource.effect and self.resource.color_mode.mode == "sequence")
            else None
        )

    @property
    def effect_list(self) -> list[str] | None:
        """Get all available effects for the light."""
        all_effects = []
        for effects in self.resource.effect.effects.values() or []:
            all_effects.extend(effects)
        return all_effects or None

    @property
    def is_on(self) -> bool | None:
        """Determine if the light is currently on."""
        return self.resource.is_on

    @property
    def max_color_temp_kelvin(self) -> int | None:
        """Get the lights maximum temperature color."""
        return (
            max(self.resource.color_temperature.supported)
            if self.resource.color_temperature
            else None
        )

    @property
    def min_color_temp_kelvin(self) -> int | None:
        """Get the lights minimum temperature color."""
        return (
            min(self.resource.color_temperature.supported)
            if self.resource.color_temperature
            else None
        )

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Get the lights current RGB colors."""
        if not self.resource.color:
            return None
        if self.color_mode == ColorMode.WHITE:
            return None
        return (
            self.resource.color.red,
            self.resource.color.green,
            self.resource.color.blue,
        )

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Get all supported color modes."""
        return self._attr_supported_color_modes

    @property
    def supported_features(self) -> LightEntityFeature:
        """Get all supported light features."""
        if self.resource.effect:
            return LightEntityFeature(0) | LightEntityFeature.EFFECT
        return LightEntityFeature(0)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn device on."""
        brightness: int | None = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(brightness_to_value((1, 100), kwargs[ATTR_BRIGHTNESS]))
        temperature: int | None = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        color: tuple[int, int, int] | None = kwargs.get(ATTR_RGB_COLOR)
        effect: str | None = kwargs.get(ATTR_EFFECT)
        white = kwargs.get(ATTR_WHITE)
        color_mode: str | None = None
        if color:
            color_mode = "color"
        elif effect:
            color_mode = "sequence"
        elif (
            temperature and self.resource.supports_color_temperature
        ) or wants_api_white(self.resource, kwargs, white):
            color_mode = "white"
        if type(white) is int:
            brightness = int(brightness_to_value((1, 100), white))
        elif white is True or (ATTR_WHITE in kwargs and white is None):
            if brightness is None:
                brightness = default_brightness_pct(self.resource)
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

    async def async_turn_off(self, **kwargs) -> None:
        """Turn device off."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=False,
        )


def is_api_white_zone(resource: Light) -> bool:
    """Return True for zones that use API color-mode white without CCT."""
    return resource.supports_color_white and not resource.supports_color_temperature


def wants_api_white(resource: Light, kwargs: dict, white: bool | int | None) -> bool:
    """Return True when the call should PUT API color-mode white."""
    if not is_api_white_zone(resource):
        return False
    if white is True or type(white) is int:
        return True
    # HA more-info white button sends ``white: true``, which core may convert to
    # ``None`` when ``light.brightness`` was unavailable at preprocess time.
    if ATTR_WHITE in kwargs:
        return True
    return resource.color_mode is not None and resource.color_mode.mode == "white"


def default_brightness_pct(resource: Light) -> int:
    """Return a 1..100 brightness for white-mode commands."""
    if resource.dimming and resource.brightness is not None:
        return int(resource.brightness)
    return 100


def get_color_mode(resource: Light, supported_modes: set[ColorMode]) -> ColorMode:
    """Determine the correct mode.

    :param resource: Light from aioafero
    :param supported_modes: Supported color modes
    """
    if not resource.color_mode:
        return list(supported_modes)[0] if len(supported_modes) else ColorMode.ONOFF
    if resource.color_mode.mode == "color":
        return ColorMode.RGB
    if resource.color_mode.mode == "white":
        if ColorMode.COLOR_TEMP in supported_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.WHITE in supported_modes:
            return ColorMode.WHITE
        if ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
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
