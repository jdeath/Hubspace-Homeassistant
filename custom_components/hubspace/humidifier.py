"""Home Assistant entity for interacting with Afero dehumidifiers."""

from functools import partial
from typing import Any

from aioafero.v1 import AferoBridgeV1, DehumidifierController
from aioafero.v1.controllers.event import EventType
from aioafero.v1.models import Dehumidifier
from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class HubspaceDehumidifier(HubspaceBaseEntity, HumidifierEntity):
    """Representation of an Afero dehumidifier."""

    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: DehumidifierController,
        resource: Dehumidifier,
    ) -> None:
        """Initialize an Afero dehumidifier."""
        super().__init__(bridge, controller, resource)
        if self.resource.mode:
            self._attr_supported_features = HumidifierEntityFeature.MODES

    @property
    def is_on(self) -> bool:
        """Return whether the dehumidifier is powered on."""
        return self.resource.on.on

    @property
    def current_humidity(self) -> int | None:
        """Return the measured relative humidity."""
        return self.resource.current_humidity

    @property
    def target_humidity(self) -> int:
        """Return the relative humidity the unit is trying to reach."""
        return self.resource.target_humidity.value

    @property
    def min_humidity(self) -> float:
        """Return the lowest settable target humidity."""
        return self.resource.target_humidity.min

    @property
    def max_humidity(self) -> float:
        """Return the highest settable target humidity."""
        return self.resource.target_humidity.max

    @property
    def mode(self) -> str | None:
        """Return the active mode."""
        return self.resource.mode.mode if self.resource.mode else None

    @property
    def available_modes(self) -> list[str] | None:
        """Return all modes the unit supports."""
        return sorted(self.resource.mode.modes) if self.resource.mode else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dehumidifier on."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, on=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dehumidifier off."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, on=False
        )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set a new target humidity, snapped to the unit's step."""
        step = self.resource.target_humidity.step
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            target_humidity=int(round(humidity / step) * step),
        )

    async def async_set_mode(self, mode: str) -> None:
        """Set a new mode."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, mode=mode
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: DehumidifierController = api.dehumidifiers
    make_entity = partial(HubspaceDehumidifier, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Dehumidifier) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
