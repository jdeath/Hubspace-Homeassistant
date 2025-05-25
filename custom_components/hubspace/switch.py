"""Home Assistant entity for interacting with Afero Switch."""

from functools import partial
from typing import Any

from aioafero.v1 import AferoBridgeV1
from aioafero.v1.controllers.event import EventType
from aioafero.v1.controllers.switch import SwitchController
from aioafero.v1.models.switch import Switch
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator


class HubspaceSwitch(HubspaceBaseEntity, SwitchEntity):
    """Representation of an Afero switch."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: SwitchController,
        resource: Switch,
        instance: str | None,
    ) -> None:
        """Initialize an Afero switch."""
        super().__init__(bridge, controller, resource, instance=instance)
        self.instance = instance

    @property
    def is_on(self) -> bool | None:
        """Determines if the switch is on."""
        feature = self.resource.on.get(self.instance, None)
        if feature:
            return feature.on
        return None

    @update_decorator
    async def async_turn_on(
        self,
        **kwargs: Any,
    ) -> None:
        """Turn on the entity."""
        self.logger.debug("Adjusting entity %s with %s", self.resource.id, kwargs)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=True,
            instance=self.instance,
        )

    @update_decorator
    async def async_turn_off(
        self,
        **kwargs: Any,
    ) -> None:
        """Turn off the entity."""
        self.logger.debug("Adjusting entity %s with %s", self.resource.id, kwargs)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            on=False,
            instance=self.instance,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: SwitchController = api.switches
    make_entity = partial(HubspaceSwitch, bridge, controller)

    def get_unique_entities(hs_resource: Switch) -> list[HubspaceSwitch]:
        instances = hs_resource.on.keys()
        return [
            make_entity(hs_resource, instance)
            for instance in instances
            if len(instances) == 1 or instance is not None
        ]

    @callback
    def async_add_entity(event_type: EventType, hs_resource: Switch) -> None:
        """Add an entity."""
        async_add_entities(get_unique_entities(hs_resource))

    # add all current items in controller
    entities: list[HubspaceSwitch] = []
    for resource in controller:
        entities.extend(get_unique_entities(resource))
    async_add_entities(entities)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
