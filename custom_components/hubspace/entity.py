"""Generic Hubspace Entity Model."""

from __future__ import annotations

from functools import wraps

from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.controllers.event import EventType
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .bridge import HubspaceBridge
from .const import DOMAIN


class HubspaceBaseEntity(Entity):  # pylint: disable=hass-enforce-class-module
    """Generic Entity Class for a Hubspace resource."""

    _attr_should_poll = False

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
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
        self._attr_has_entity_name = bool(self.resource.device_information.name)

        if instance is not False:
            self._attr_name = instance if instance else type(self.resource).__name__
        elif getattr(self.resource, "split_identifier", None) is not None:
            self._attr_name = self.resource.id.rsplit(
                f"-{self.resource.split_identifier}-", 1
            )[1]
        else:
            self._attr_name = type(self.resource).__name__

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.resource.device_information.parent_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Call when an entity is added."""
        self.async_on_remove(
            self.controller.subscribe(
                self.handle_event,
                id_filter=self.resource.id,
                event_filter=EventType.RESOURCE_UPDATED,
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
    def handle_event(self, event_type: EventType, resource) -> None:
        """Handle status event for this resource (or it's parent)."""
        self.logger.debug("Received status update for %s", self.entity_id)
        self.on_update()
        self.async_write_ha_state()


def update_decorator(method):
    """Force HA to automatically update.

    Hubspace can be slow to update, which causes a delay between HA UI
    and what the user just did. Force it to take the new states right
    away.
    """

    @wraps(method)
    async def _impl(*args, **kwargs):
        res = await method(*args, **kwargs)
        ha_entity: HubspaceBaseEntity = args[0]
        ha_entity.handle_event(EventType.RESOURCE_UPDATED, None)
        return res

    return _impl
