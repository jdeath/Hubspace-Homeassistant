"""Home Assistant entity for getting state from Afero sensors."""

import logging
from typing import Any

from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.controllers.event import EventType
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN, SENSORS_GENERAL
from .entity import HubspaceBaseEntity

LOGGER = logging.getLogger(__name__)


class AferoSensorEntity(HubspaceBaseEntity, SensorEntity):
    """Representation of an Afero sensor."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        sensor: str,
    ) -> None:
        """Initialize an Afero sensor."""
        super().__init__(bridge, controller, resource, instance=sensor)
        self.entity_description: SensorEntityDescription = SENSORS_GENERAL.get(sensor)
        self._attr_name = sensor

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        return self.resource.sensors[self._attr_name].value


def get_sensors(
    bridge: HubspaceBridge, controller: AferoController, resource: AferoModelResource
) -> list[AferoSensorEntity]:
    """Get all sensors for a given resource."""
    sensor_entities: list[AferoSensorEntity] = []
    for sensor in resource.sensors:
        if sensor not in SENSORS_GENERAL:
            LOGGER.warning(
                "Unknown sensor %s found in %s %s. Please open a bug report",
                sensor,
                type(controller).__name__,
                resource.device_information.name,
            )
            continue
        sensor_entities.append(AferoSensorEntity(bridge, controller, resource, sensor))
    return sensor_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]

    for controller in bridge.api.controllers:
        # Listen for new devices
        if not controller.ITEM_SENSORS:
            continue
        config_entry.async_on_unload(
            controller.subscribe(
                await generate_callback(bridge, controller, async_add_entities),
                event_filter=EventType.RESOURCE_ADDED,
            )
        )
        # Add any currently tracked entities
        for resource in controller:
            if sensors := get_sensors(bridge, controller, resource):
                async_add_entities(sensors)


async def generate_callback(bridge, controller, async_add_entities: callback):
    """Generate a callback function for handling new sensor entities.

    Args:
        bridge: HubspaceBridge instance for managing device communication
        controller: AferoController instance managing the device
        async_add_entities: Callback function to register new entities

    Returns:
        Callback function that adds new sensor entities when resources are added

    """

    async def add_entity_controller(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add an entity."""
        if sensors := get_sensors(bridge, controller, resource):
            async_add_entities(sensors)

    return add_entity_controller
