"""Home Assistant entity for interacting with Afero Select."""

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


class AferoSelectEntitiy(HubspaceBaseEntity, SelectEntity):
    """Representation of an Afero Select."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        identifier: tuple[str, str],
    ) -> None:
        """Initialize an Afero Select."""

        super().__init__(bridge, controller, resource, instance=str(identifier))
        self._identifier: tuple[str, str] = identifier
        self._attr_name = resource.selects[identifier].name

    @property
    def current_option(self) -> str:
        """The current select option."""
        return str(self.resource.selects[self._identifier].selected)

    @property
    def options(self) -> list:
        """A list of available options as strings."""
        return sorted([str(x) for x in self.resource.selects[self._identifier].selects])

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

    # add all current items in the controller
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
        # Add any currently tracked entities
        entities.extend(
            [
                AferoSelectEntitiy(bridge, controller, resource, select)
                for resource in controller
                for select in resource.selects
            ]
        )

    async_add_entities(entities)


async def generate_callback(bridge, controller, async_add_entities: callback):
    """Generate a callback function for handling new select entities.

    Args:
        bridge: HubspaceBridge instance for managing device communication
        controller: AferoController instance managing the device
        async_add_entities: Callback function to register new entities

    Returns:
        Callback function that adds new select entities when resources are added

    """

    async def add_entity_controller(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add one or more Selects."""
        async_add_entities(
            [
                AferoSelectEntitiy(bridge, controller, resource, select)
                for select in resource.selects
            ]
        )

    return add_entity_controller
