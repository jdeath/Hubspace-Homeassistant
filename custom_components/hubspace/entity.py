"""Generic Hubspace Entity Model."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from aioafero.v1.controllers.base import BaseResourcesController
from aioafero.v1.controllers.event import EventType
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .bridge import HubspaceBridge
from .const import DOMAIN

if TYPE_CHECKING:
    from aioafero.v1.models import (
        Device,
        Fan,
        AferoSensor,
        Light,
        Lock,
        Switch,
        Valve,
    )

    type HubspaceResource = Device | Fan | Light | Lock | AferoSensor | Switch | Valve


class HubspaceBaseEntity(Entity):  # pylint: disable=hass-enforce-class-module
    """Generic Entity Class for a Hubspace resource."""

    _attr_should_poll = False

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: BaseResourcesController,
        resource: HubspaceResource,
        instance: str | None | bool = False,
    ) -> None:
        """Initialize a generic Hubspace resource entity."""
        self.bridge = bridge
        self.controller = controller
        self.resource = resource
        self.logger = bridge.logger.getChild(resource.type.value)

        # Entity class attributes
        unique_id = f"{resource.id}.{instance}" if instance else resource.id
        self._attr_unique_id = unique_id or resource.id
        self._attr_has_entity_name = (
            True if self.resource.device_information.name else False
        )

        if instance is not False:
            self._attr_name = instance if instance else type(self.resource).__name__
        else:
            self._attr_name = type(self.resource).__name__

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.resource.device_information.parent_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        self.async_on_remove(
            self.controller.subscribe(
                self._handle_event,
                self.resource.id,
                EventType.RESOURCE_UPDATED,
            )
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""
        # entities without a device attached should be always available
        if self.resource is None:
            return True
        return self.resource.available

    @callback
    def on_update(self) -> None:
        """Call on update event."""
        # a subclass can override this is required, but its probably
        # not needed

    @callback
    def _handle_event(self, event_type: EventType, resource) -> None:
        """Handle status event for this resource (or it's parent)."""
        self.logger.debug("Received status update for %s", self.entity_id)
        self.on_update()
        self.async_write_ha_state()


def update_decorator(method):
    """Force HA to automatically update

    Hubspace can be slow to update which causes a delay between HA UI
    and what the user just did. Force it to take the new states right
    away.
    """

    @wraps(method)
    async def _impl(*args, **kwargs):
        res = await method(*args, **kwargs)
        args[0]._handle_event(EventType.RESOURCE_UPDATED, None)
        return res

    return _impl
