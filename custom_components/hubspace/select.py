from dataclasses import fields

from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.controllers.event import EventType
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class AferoNumberEntity(HubspaceBaseEntity, SelectEntity):
    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        identifier: tuple[str, str],
    ) -> None:
        super().__init__(bridge, controller, resource, instance=str(identifier))
        self._identifier: tuple[str, str] = identifier
        self._attr_name = resource.selects[identifier].name

    @property
    def current_option(self) -> str:
        return self.resource.selects[self._identifier].selected

    @property
    def options(self) -> list:
        return sorted(list(self.resource.selects[self._identifier].selects))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            selects={
                self._identifier: option,
            },
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]

    # add all current items in controller
    entities = []
    for controller in bridge.api.controllers:
        if "selects" not in [x.name for x in fields(controller.ITEM_CLS)]:
            continue
        config_entry.async_on_unload(
            controller.subscribe(
                await generate_callback(bridge, controller, async_add_entities),
                event_filter=EventType.RESOURCE_ADDED,
            )
        )
        # Add any currently-tracked entities
        for resource in controller:
            # Listen for new devices
            for select in resource.selects.keys():
                entities.append(AferoNumberEntity(bridge, controller, resource, select))

    async_add_entities(entities)


async def generate_callback(bridge, controller, async_add_entities: callback):

    async def add_entity_controller(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add an entity."""
        for number in resource.selects.keys():
            async_add_entities(
                [AferoNumberEntity(bridge, controller, resource, number)]
            )

    return add_entity_controller
