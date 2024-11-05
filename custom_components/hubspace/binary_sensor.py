import logging
from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice

from . import HubSpaceConfigEntry
from .const import ENTITY_BINARY_SENSOR
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


class HubSpaceBinarySensor(HubSpaceEntity, BinarySensorEntity):
    """HubSpace child sensor component

    :ivar _function_class: functionClass within the payload
    :ivar _function_instance: functionInstance within the payload
    :ivar _sensor_value: Current value of the sensor
    """

    ENTITY_TYPE: str = ENTITY_BINARY_SENSOR

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
        device: HubSpaceDevice,
    ) -> None:
        self.entity_description = description
        search_data = description.key.split("|", 1)
        self._function_class: str
        self._function_instance: Optional[str] = None
        try:
            self._function_class, self._function_instance = search_data
        except ValueError:
            self._function_class = search_data
        self._sensor_value: Optional[str] = None
        super().__init__(coordinator, device)

    def update_states(self) -> None:
        """Handle updated data from the coordinator."""
        for state in self.get_device_states():
            if state.functionClass == self._function_class:
                if (
                    self._function_instance
                    and self._function_instance != state.functionInstance
                ):
                    continue
                self._sensor_value = state.value

    @property
    def device_class(self) -> Any:
        """Return the state."""
        return self.entity_description.device_class

    @property
    def is_on(self) -> bool:
        return self._sensor_value != "normal"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Sensor entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    entities: list[HubSpaceBinarySensor] = []
    for dev_sensors in coordinator_hubspace.data[ENTITY_BINARY_SENSOR].values():
        dev = dev_sensors["device"]
        for sensor in dev_sensors["sensors"]:
            _LOGGER.debug(
                "Adding a binary sensor from %s [%s] - %s",
                dev.friendly_name,
                dev.id,
                sensor.key,
            )
            ha_entity = HubSpaceBinarySensor(coordinator_hubspace, sensor, dev)
            entities.append(ha_entity)
    async_add_entities(entities)
