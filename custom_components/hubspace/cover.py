"""Home Assistant entity for interacting with Afero blinds."""

from functools import partial
from typing import Any

from aioafero.v1 import AferoBridgeV1, BlindsController
from aioafero.v1.controllers.event import EventType
from aioafero.v1.models import Blinds
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class HubspaceBlinds(HubspaceBaseEntity, CoverEntity):
    """Representation of an Afero blinds zone.

    A zone moves every blind assigned to it. Afero reports the position as a
    percentage where 100 is fully open, which matches Home Assistant.
    """

    _attr_device_class = CoverDeviceClass.BLIND

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: BlindsController,
        resource: Blinds,
    ) -> None:
        """Initialize an Afero blinds zone."""
        super().__init__(bridge, controller, resource)
        # Zones share the Smart Blinds Gateway device, so name each by its zone.
        # Afero names can carry stray whitespace.
        if zone_name := (resource.device_information.name or "").strip():
            self._attr_name = zone_name

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Return the features the zone supports."""
        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if self.resource.position is not None:
            features |= CoverEntityFeature.SET_POSITION
        if "stop" in self.resource.commands.get("stop-moving", set()):
            features |= CoverEntityFeature.STOP
        return features

    @property
    def current_cover_position(self) -> int | None:
        """Return the position, 0 (closed) to 100 (open)."""
        position = self.resource.position
        return position.position if position else None

    @property
    def is_closed(self) -> bool | None:
        """Return whether the blinds are fully closed."""
        position = self.current_cover_position
        return None if position is None else position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Fully open the blinds."""
        await self.bridge.async_request_call(
            self.controller.open, device_id=self.resource.id
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Fully close the blinds."""
        await self.bridge.async_request_call(
            self.controller.close, device_id=self.resource.id
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the blinds to a position."""
        await self.bridge.async_request_call(
            self.controller.set_position,
            device_id=self.resource.id,
            position=kwargs[ATTR_POSITION],
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the blinds if they are moving."""
        await self.bridge.async_request_call(
            self.controller.stop, device_id=self.resource.id
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: BlindsController = api.blinds
    make_entity = partial(HubspaceBlinds, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Blinds) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
