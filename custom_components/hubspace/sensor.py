from functools import partial
from typing import Any

from aioafero.v1 import AferoBridgeV1
from aioafero.v1.controllers.device import DeviceController
from aioafero.v1.controllers.event import EventType
from aioafero.v1.models.device import Device
from aioafero.v1.models.sensor import AferoSensor
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
        controller: DeviceController,
        resource: Device,
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
    api: AferoBridgeV1 = bridge.api
    controller: DeviceController = api.devices
    make_entity = partial(AferoSensorEntity, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: AferoSensor) -> None:
        """Add an entity."""
        for sensor in resource.sensors.keys():
            async_add_entities([make_entity(resource, sensor)])

    # add all current items in controller
    sensor_entities = []
    for entity in controller:
        for sensor in entity.sensors.keys():
            if sensor in SENSORS_GENERAL:
                sensor_entities.append(make_entity(entity, sensor))
    async_add_entities(sensor_entities)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
