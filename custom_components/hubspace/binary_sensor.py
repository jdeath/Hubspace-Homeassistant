from functools import partial

from aioafero import EventType
from aioafero.v1 import DeviceController, AferoBridgeV1
from aioafero.v1.models import Device, AferoSensor
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


class HubspaceBinarySensorEntity(HubspaceBaseEntity, BinarySensorEntity):
    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: DeviceController,
        resource: Device,
        sensor: str,
    ) -> None:
        super().__init__(
            bridge,
            controller,
            resource,
            instance=sensor,
        )
        self.entity_description: BinarySensorEntityDescription = BINARY_SENSORS.get(
            sensor
        )
        self._attr_name = sensor

    @property
    def is_on(self) -> bool:
        """Return the current value"""
        return self.resource.binary_sensors[self._attr_name].value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: DeviceController = api.devices
    make_entity = partial(HubspaceBinarySensorEntity, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: AferoSensor) -> None:
        """Add an entity."""
        for sensor in resource.binary_sensors.keys():
            async_add_entities([make_entity(resource, sensor)])

    # add all current items in controller
    sensor_entities = []
    for entity in controller:
        for sensor in entity.binary_sensors.keys():
            if sensor not in BINARY_SENSORS:
                controller._logger.warning(
                    "Unknown sensor %s found in %s. Please open a bug report",
                    sensor,
                    entity.id,
                )
                continue
            sensor_entities.append(make_entity(entity, sensor))
    async_add_entities(sensor_entities)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
