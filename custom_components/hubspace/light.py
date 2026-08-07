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

NIGHT_LIGHT_MODE = "night-light"


class HubspaceLight(HubspaceBaseEntity, LightEntity):
    """Representation of an Afero light."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: LightController,
        resource: Light,
        channel: str | None = None,
    ) -> None:
        """Initialize an Afero light.

        :param channel: For dual-channel fixtures presented as two entities,
            ``color`` or ``white``. ``None`` for a single combined light.
        """
        super().__init__(
            bridge,
            controller,
            resource,
            instance=channel if channel is not None else False,
        )
        self._channel = channel
        self._supported_features: LightEntityFeature = LightEntityFeature(0)
        supported_color_modes = {ColorMode.ONOFF}
        if self._supports_rgb():
            supported_color_modes.add(ColorMode.RGB)
        if self._supports_color_temp():
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        if (
            self._channel is None
            and is_api_white_zone(self.resource)
            and self.resource.supports_color
        ):
            # Trim-style zones: API warm white via color-mode white (no CCT slider).
            # HA requires RGB alongside WHITE in supported_color_modes.
            supported_color_modes.add(ColorMode.WHITE)
        if self.resource.supports_dimming or (
            self._channel
            and self.resource.channel_brightness(self._channel) is not None
        ):
            supported_color_modes.add(ColorMode.BRIGHTNESS)
        self._attr_supported_color_modes = filter_supported_color_modes(
            supported_color_modes
        )

    def _supports_rgb(self) -> bool:
        if self._channel == "white":
            return False
        return self.resource.supports_color

    def _supports_color_temp(self) -> bool:
        if self._channel == "color":
            return False
        return self.resource.supports_color_temperature

    @property
    def brightness(self) -> int | None:
        """The brightness of this light between 1..255."""
        pct = displayed_brightness_pct(self.resource, channel=self._channel)
        if pct is None:
            return None
        return value_to_brightness((1, 100), pct)

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        """Expose dual-channel brightness and API mode for automations."""
        attrs: dict[str, int | str] = {}
        if self.resource.is_dual_channel and self._channel is None:
            for name, channel in self.resource.channels.items():
                if channel.brightness is not None:
                    attrs[f"{name}_brightness_pct"] = int(channel.brightness)
            if self.resource.color_mode is not None:
                attrs["api_color_mode"] = self.resource.color_mode.mode
        return attrs

    @property
    def color_mode(self) -> ColorMode:
        """Get the current color mode for the light."""
        return get_color_mode(
            self.resource, self._attr_supported_color_modes, channel=self._channel
        )

    @property
    def color_temp_kelvin(self) -> int | None:
        """Get the current color temperature for the light."""
        if self._channel == "color" or not self.resource.color_temperature:
            return None
        return self.resource.color_temperature.temperature

    @property
    def effect(self) -> str | None:
        """Get the current effect for the light."""
        if self._channel == "white":
            return None
        return (
            self.resource.effect.effect
            if (self.resource.effect and self.resource.color_mode.mode == "sequence")
            else None
        )

    @property
    def effect_list(self) -> list[str] | None:
        """Get all available effects for the light."""
        if self._channel == "white" or not self.resource.effect:
            return None
        all_effects = []
        for effects in self.resource.effect.effects.values() or []:
            all_effects.extend(effects)
        return all_effects or None

    @property
    def is_on(self) -> bool | None:
        """Determine if the light is currently on.

        When night-light mode is active the dedicated night-light entity owns
        that state, so the main / channel lights report off.
        """
        if (
            self.resource.color_mode
            and self.resource.color_mode.mode == NIGHT_LIGHT_MODE
        ):
            return False
        if self._channel:
            channel_on = self.resource.channel_on(self._channel)
            if channel_on is not None:
                return channel_on
        return self.resource.is_on

    @property
    def max_color_temp_kelvin(self) -> int | None:
        """Get the lights maximum temperature color."""
        if not self._supports_color_temp() or not self.resource.color_temperature:
            return None
        return max(self.resource.color_temperature.supported)

    @property
    def min_color_temp_kelvin(self) -> int | None:
        """Get the lights minimum temperature color."""
        if not self._supports_color_temp() or not self.resource.color_temperature:
            return None
        return min(self.resource.color_temperature.supported)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Get the lights current RGB colors."""
        if not self._supports_rgb() or not self.resource.color:
            return None
        if self.color_mode == ColorMode.WHITE:
            return None
        if self.color_mode == ColorMode.COLOR_TEMP and api_color_mode_is_mixed(
            self.resource
        ):
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
        if self._channel == "white":
            return LightEntityFeature(0)
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
                brightness = default_brightness_pct(
                    self.resource, channel=self._channel
                )
        if self._channel and color_mode is None:
            color_mode = "color" if self._channel == "color" else "white"
        leaving_night_light = (
            self.resource.color_mode is not None
            and self.resource.color_mode.mode == NIGHT_LIGHT_MODE
        )
        # Stored mode is night-light while that entity is active; restore the
        # prior mode so the main light does not resume night-light on power-on.
        if leaving_night_light and color_mode is None:
            color_mode = self.bridge.night_light_previous_modes.get(
                self.resource.id, "white"
            )
        # aioafero only mode-before-powers for no-brightness *targets*; restoring
        # to white/color/sequence while off needs an explicit mode PUT first.
        if (
            leaving_night_light
            and not self.resource.is_on
            and color_mode
            and color_mode != NIGHT_LIGHT_MODE
        ):
            await self.bridge.async_request_call(
                self.controller.set_state,
                device_id=self.resource.id,
                color_mode=color_mode,
            )
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            brightness=brightness,
            temperature=temperature,
            color=color,
            color_mode=color_mode,
            effect=effect,
            channel=self._channel,
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn device off."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=False,
            channel=self._channel,
        )


class HubspaceNightLight(HubspaceBaseEntity, LightEntity):
    """Night-light color-mode as a separate on/off light."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: LightController,
        resource: Light,
    ) -> None:
        """Initialize an Afero night light."""
        super().__init__(bridge, controller, resource, instance=NIGHT_LIGHT_MODE)
        self._attr_name = "Night Light"

    @property
    def is_on(self) -> bool | None:
        """Return True when powered on in night-light color-mode."""
        if self.resource.color_mode is None:
            return None
        return self.resource.is_on and self.resource.color_mode.mode == NIGHT_LIGHT_MODE

    async def async_turn_on(self, **kwargs) -> None:
        """Enable night-light color-mode."""
        self.bridge.night_light_was_on[self.resource.id] = self.resource.is_on
        if (
            self.resource.color_mode
            and self.resource.color_mode.mode != NIGHT_LIGHT_MODE
        ):
            self.bridge.night_light_previous_modes[self.resource.id] = (
                self.resource.color_mode.mode
            )
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            color_mode=NIGHT_LIGHT_MODE,
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Leave night-light without flashing another mode on turn-off."""
        previous = self.bridge.night_light_previous_modes.get(self.resource.id, "white")
        # After reload / external enable we may lack was_on; prefer staying on in
        # a normal mode over unexpectedly powering the fixture off.
        was_on = self.bridge.night_light_was_on.get(self.resource.id, True)
        if was_on:
            await self.bridge.async_request_call(
                self.controller.set_state,
                device_id=self.resource.id,
                on=True,
                color_mode=previous,
            )
        else:
            await self.bridge.async_request_call(
                self.controller.set_state,
                device_id=self.resource.id,
                on=False,
            )


def has_night_light_mode(resource: Light) -> bool:
    """Return True when the light advertises night-light color-mode."""
    return NIGHT_LIGHT_MODE in (resource.color_modes or [])


def should_split_dual_channel_light(resource: Light) -> bool:
    """Return True when this dual-channel fixture should be two HA light entities.

    Each color/white channel becomes its own light. aioafero keeps one API light
    and handles ``mixed`` when both channels are on.
    """
    if not getattr(resource, "is_dual_channel", False):
        return False
    return {"color", "white"}.issubset(resource.channels)


def entities_for_light(
    bridge: HubspaceBridge, controller: LightController, resource: Light
) -> list[HubspaceLight | HubspaceNightLight]:
    """Build light entities for a resource (channels + optional night-light)."""
    if should_split_dual_channel_light(resource):
        entities: list[HubspaceLight | HubspaceNightLight] = [
            HubspaceLight(bridge, controller, resource, channel="color"),
            HubspaceLight(bridge, controller, resource, channel="white"),
        ]
    else:
        entities = [HubspaceLight(bridge, controller, resource)]
    if has_night_light_mode(resource):
        entities.append(HubspaceNightLight(bridge, controller, resource))
    return entities


def api_color_mode_is_mixed(resource: Light) -> bool:
    """Return True when the fixture has both color and white channels active."""
    return resource.color_mode is not None and resource.color_mode.mode == "mixed"


def displayed_brightness_pct(
    resource: Light, *, channel: str | None = None
) -> int | None:
    """Return the brightness percentage shown on the HA light slider."""
    if channel:
        pct = resource.channel_brightness(channel)
        if pct is not None:
            return int(pct)
        if not resource.dimming:
            return None
        return int(resource.brightness) if resource.brightness is not None else 100
    if not resource.dimming:
        return None
    if not resource.is_dual_channel:
        pct = resource.brightness
        return int(pct) if pct is not None else 100
    api_mode = resource.color_mode.mode if resource.color_mode else None
    if api_mode in ("color", "sequence"):
        pct = resource.channel_brightness("color") or resource.brightness
    elif api_mode == "white":
        pct = resource.channel_brightness("white") or resource.brightness
    else:
        pct = resource.brightness
    return int(pct) if pct is not None else 100


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


def default_brightness_pct(resource: Light, *, channel: str | None = None) -> int:
    """Return a 1..100 brightness for white-mode commands."""
    pct = displayed_brightness_pct(resource, channel=channel)
    if pct is not None:
        return pct
    return 100


def get_color_mode(
    resource: Light,
    supported_modes: set[ColorMode],
    *,
    channel: str | None = None,
) -> ColorMode:
    """Determine the correct mode.

    :param resource: Light from aioafero
    :param supported_modes: Supported color modes
    :param channel: Optional dual-entity channel filter
    """
    if channel == "color":
        if ColorMode.RGB in supported_modes:
            return ColorMode.RGB
        if ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
    if channel == "white":
        if ColorMode.COLOR_TEMP in supported_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
    if not resource.color_mode:
        return _preferred_supported_color_mode(supported_modes)
    if resource.color_mode.mode == "color":
        return ColorMode.RGB
    if resource.color_mode.mode == "mixed":
        if ColorMode.COLOR_TEMP in supported_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.RGB in supported_modes:
            return ColorMode.RGB
        if ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
    if resource.color_mode.mode == "white":
        if ColorMode.COLOR_TEMP in supported_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.WHITE in supported_modes:
            return ColorMode.WHITE
        if ColorMode.BRIGHTNESS in supported_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF
    return _preferred_supported_color_mode(supported_modes)


def _preferred_supported_color_mode(supported_modes: set[ColorMode]) -> ColorMode:
    """Pick a stable color mode when API mode is missing or unknown."""
    for mode in (
        ColorMode.RGB,
        ColorMode.COLOR_TEMP,
        ColorMode.WHITE,
        ColorMode.BRIGHTNESS,
        ColorMode.ONOFF,
    ):
        if mode in supported_modes:
            return mode
    return ColorMode.ONOFF


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: LightController = api.lights
    make_entities = partial(entities_for_light, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Light) -> None:
        """Add an entity."""
        async_add_entities(make_entities(resource))

    entities: list[HubspaceLight | HubspaceNightLight] = []
    for resource in controller:
        entities.extend(make_entities(resource))
    async_add_entities(entities)
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
