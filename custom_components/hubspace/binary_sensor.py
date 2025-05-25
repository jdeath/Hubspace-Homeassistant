"""Home Assistant entity for getting state from Afero binary sensors."""

import logging

from aioafero import EventType
from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.models import AferoBinarySensor
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import BINARY_SENSORS, DOMAIN
from .entity import HubspaceBaseEntity

LOGGER = logging.getLogger(__name__)


class AferoBinarySensorEntity(HubspaceBaseEntity, BinarySensorEntity):
    """Representation of an Afero binary sensor."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        sensor: str,
    ) -> None:
        """Initialize an Afero binary sensor."""
        super().__init__(
            bridge,
            controller,
            resource,
            instance=sensor,
        )
        self.entity_description: BinarySensorEntityDescription = BINARY_SENSORS.get(
            sensor
        )
        self._attr_name = self.entity_description.name

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on."""
        return self.resource.binary_sensors[self.entity_description.key].value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]

    # add all current items in controller
    sensor_entities = []
    for controller in bridge.api.controllers:
        # Listen for new devices
        config_entry.async_on_unload(
            controller.subscribe(
                await generate_callback(bridge, controller, async_add_entities),
                event_filter=EventType.RESOURCE_ADDED,
            )
        )
        # Add any currently tracked entities
        for resource in controller:
            if not hasattr(resource, "binary_sensors"):
                continue
            for sensor in resource.binary_sensors:
                if sensor not in BINARY_SENSORS:
                    LOGGER.warning(
                        "Unknown sensor %s found in %s. Please open a bug report",
                        sensor,
                        resource.id,
                    )
                    continue
                if sensor in BINARY_SENSORS:
                    sensor_entities.append(
                        AferoBinarySensorEntity(bridge, controller, resource, sensor)
                    )

    async_add_entities(sensor_entities)


async def generate_callback(bridge, controller, async_add_entities: callback):
    """Generate a callback function for handling new binary sensor entities.

    Args:
        bridge: HubspaceBridge instance for managing device communication
        controller: AferoController instance managing the device
        async_add_entities: Callback function to register new entities

    Returns:
        Callback function that adds new binary sensor entities when resources are added

    """

    async def add_entity_controller(
        event_type: EventType, resource: AferoBinarySensor
    ) -> None:
        """Add an entity."""
        async_add_entities(
            [
                AferoBinarySensorEntity(bridge, controller, resource, sensor)
                for sensor in resource.binary_sensors
                if sensor in BINARY_SENSORS
            ]
        )

    return add_entity_controller
