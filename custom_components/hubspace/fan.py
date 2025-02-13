from functools import partial
from typing import Any, Optional

from aiohubspace import EventType
from aiohubspace.v1 import FanController, HubspaceBridgeV1
from aiohubspace.v1.models import Fan
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator

PRESET_HS_TO_HA = {"comfort-breeze": "breeze"}


class HubspaceFan(HubspaceBaseEntity, FanEntity):
    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: FanController,
        resource: Fan,
    ) -> None:
        super().__init__(bridge, controller, resource)
        self._supported_features: FanEntityFeature = FanEntityFeature(0)
        if self.resource.supports_on:
            self._supported_features |= FanEntityFeature.TURN_ON
            self._supported_features |= FanEntityFeature.TURN_OFF
        if self.resource.supports_direction:
            self._supported_features |= FanEntityFeature.DIRECTION
        if self.resource.supports_speed:
            self._supported_features |= FanEntityFeature.SET_SPEED
        if self.resource.supports_presets:
            self._supported_features |= FanEntityFeature.PRESET_MODE

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def is_on(self) -> bool | None:
        """Return true if fan is spinning"""
        return (
            self.resource.is_on
            if self._supported_features & FanEntityFeature.TURN_ON
            else None
        )

    @property
    def current_direction(self):
        return self.resource.current_direction

    @property
    def percentage(self):
        return (
            self.resource.speed.speed
            if self.supported_features & FanEntityFeature.SET_SPEED
            else None
        )

    @property
    def preset_mode(self):
        return (
            "breeze"
            if (
                self.supported_features & FanEntityFeature.PRESET_MODE
                and self.resource.preset.enabled
            )
            else None
        )

    @property
    def preset_modes(self):
        return (
            list(PRESET_HS_TO_HA.values())
            if self.supported_features & FanEntityFeature.PRESET_MODE
            else None
        )

    @property
    def speed_count(self):
        return (
            len(self.resource.speed.speeds)
            if self.supported_features & FanEntityFeature.SET_SPEED
            else None
        )

    @update_decorator
    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the entity."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            speed=percentage,
            preset=True if preset_mode else False,
        )

    @update_decorator
    async def async_turn_off(
        self,
        **kwargs: Any,
    ) -> None:
        """Turn off the fan."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=False,
        )

    @update_decorator
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            speed=percentage,
        )

    @update_decorator
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            preset=True if preset_mode else False,
        )

    @update_decorator
    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            forward=True if direction == "forward" else False,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: HubspaceBridgeV1 = bridge.api
    controller: FanController = api.fans
    make_entity = partial(HubspaceFan, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Fan) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
