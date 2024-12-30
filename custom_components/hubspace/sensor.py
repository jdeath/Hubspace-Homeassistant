from functools import partial
from typing import Any

from aiohubspace.v1 import HubspaceBridgeV1
from aiohubspace.v1.controllers.device import DeviceController
from aiohubspace.v1.controllers.event import EventType
from aiohubspace.v1.models.device import Device
from aiohubspace.v1.models.sensor import HubspaceSensor
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN, SENSORS_GENERAL
from .entity import HubspaceBaseEntity


class HubspaceSensorEntity(HubspaceBaseEntity, SensorEntity):
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
    def native_unit_of_measurement(self) -> str | None:
        return self.resource.sensors[self._attr_name].unit

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
    api: HubspaceBridgeV1 = bridge.api
    controller: DeviceController = api.devices
    make_entity = partial(HubspaceSensorEntity, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: HubspaceSensor) -> None:
        """Add an entity."""
        for sensor in resource.sensors.keys():
            async_add_entities([make_entity(resource, sensor)])

    # add all current items in controller
    sensor_entities = []
    for entity in controller:
        for sensor in entity.sensors.keys():
            if sensor not in SENSORS_GENERAL:
                controller._logger.warning(
                    "Unknown sensor %s found in %s", sensor, entity.id
                )
                continue
            sensor_entities.append(make_entity(entity, sensor))
    async_add_entities(sensor_entities)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
