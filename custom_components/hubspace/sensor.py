from typing import Any

from aioafero.v1.controllers.event import EventType
from aioafero.v1.models.sensor import AferoSensor
from aioafero.v1 import AferoController, AferoModelResource
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN, SENSORS_GENERAL
from .entity import HubspaceBaseEntity


class AferoSensorEntity(HubspaceBaseEntity, SensorEntity):
    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        sensor: str,
    ) -> None:
        super().__init__(bridge, controller, resource, instance=sensor)
        self.entity_description: SensorEntityDescription = SENSORS_GENERAL.get(sensor)
        self._attr_name = sensor

    @property
    def native_value(self) -> Any:
        """Return the current value"""
        return self.resource.sensors[self._attr_name].value


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
            controller.subscribe(await generate_callback(bridge, controller, async_add_entities), event_filter=EventType.RESOURCE_ADDED)
        )
        # Add any currently-tracked entities
        for resource in controller:
            if not hasattr(resource, "sensors"):
                continue
            for sensor in resource.sensors.keys():
                if sensor not in SENSORS_GENERAL:
                    controller._logger.warning(
                        "Unknown sensor %s found in %s. Please open a bug report",
                        sensor,
                        resource.id,
                    )
                    continue
                if sensor in SENSORS_GENERAL:
                    sensor_entities.append(AferoSensorEntity(bridge, controller, resource, sensor))

    async_add_entities(sensor_entities)


async def generate_callback(bridge, controller, async_add_entities: callback):

    async def add_entity_controller(event_type: EventType, resource: AferoSensor) -> None:
        """Add an entity."""
        for sensor in resource.sensors.keys():
            if sensor in SENSORS_GENERAL:
                async_add_entities([AferoSensorEntity(bridge, controller, resource, sensor)])


    return add_entity_controller
