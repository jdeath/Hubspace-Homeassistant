"""Home Assistant entity for interacting with Afero Number."""

from dataclasses import fields

from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.controllers.event import EventType
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator


class AferoNumberEntity(HubspaceBaseEntity, NumberEntity):
    """Representation of an Afero Number."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        identifier: tuple[str, str],
    ) -> None:
        """Initialize an Afero Number."""
        super().__init__(bridge, controller, resource, instance=str(identifier))
        self._identifier: tuple[str, str] = identifier
        self._attr_name = resource.numbers[identifier].name

    @property
    def native_max_value(self) -> float:
        """The maximum accepted value in the number's native_unit_of_measurement (inclusive)."""
        return self.resource.numbers[self._identifier].max

    @property
    def native_min_value(self) -> float:
        """The minimum accepted value in the number's native_unit_of_measurement (inclusive)."""
        return self.resource.numbers[self._identifier].min

    @property
    def native_step(self) -> float:
        """Defines the resolution of the values, i.e. the smallest increment or decrement in the number's."""
        return self.resource.numbers[self._identifier].step

    @property
    def native_value(self) -> float:
        """The value of the number in the number's native_unit_of_measurement."""
        return self.resource.numbers[self._identifier].value

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of measurement that the sensor's value is expressed in."""
        return self.resource.numbers[self._identifier].unit

    @update_decorator
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            numbers={
                self._identifier: value,
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
        if "numbers" not in [x.name for x in fields(controller.ITEM_CLS)]:
            continue
        # Listen for new devices
        config_entry.async_on_unload(
            controller.subscribe(
                await generate_callback(bridge, controller, async_add_entities),
                event_filter=EventType.RESOURCE_ADDED,
            )
        )
        # Add any currently tracked entities
        entities.extend(
            [
                AferoNumberEntity(bridge, controller, resource, number)
                for resource in controller
                for number in resource.numbers
            ]
        )
    async_add_entities(entities)


async def generate_callback(bridge, controller, async_add_entities: callback):
    """Generate a callback function for handling new number entities.

    Args:
        bridge: HubspaceBridge instance for managing device communication
        controller: AferoController instance managing the device
        async_add_entities: Callback function to register new entities

    Returns:
        Callback function that adds new number entities when resources are added

    """

    async def add_entity_controller(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add an entity."""
        async_add_entities(
            [
                AferoNumberEntity(bridge, controller, resource, number)
                for number in resource.numbers
            ]
        )

    return add_entity_controller
