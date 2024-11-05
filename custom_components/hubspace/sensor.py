import logging
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor import const as sensor_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice

from . import HubSpaceConfigEntry
from .const import ENTITY_SENSOR
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


class HubSpaceSensor(HubSpaceEntity, SensorEntity):
    """HubSpace child sensor component

    :ivar entity_description: Description of the entity
    :ivar _is_numeric: If the sensor is a numeric value
    :ivar _sensor_value: Current value of the sensor
    """

    ENTITY_TYPE = ENTITY_SENSOR

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        description: SensorEntityDescription,
        device: HubSpaceDevice,
        is_numeric: bool,
    ) -> None:
        super().__init__(coordinator, device)
        self.entity_description: SensorEntityDescription = description
        self._is_numeric: bool = is_numeric
        self._sensor_value: Optional[bool] = None

    def update_states(self) -> None:
        """Handle updated data from the coordinator."""
        for state in self.get_device_states():
            if state.functionClass == self.entity_description.key:
                if self._is_numeric and isinstance(state.value, str):
                    state.value = int("".join(i for i in state.value if i.isdigit()))
                self._sensor_value = state.value

    @property
    def native_value(self) -> Any:
        """Return the state."""
        return self._sensor_value

    @property
    def should_report(self) -> bool:
        return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Sensor entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    entities: list[HubSpaceSensor] = []
    for dev_sensors in coordinator_hubspace.data[ENTITY_SENSOR].values():
        dev = dev_sensors["device"]
        for sensor in dev_sensors["sensors"]:
            _LOGGER.debug(
                "Adding a sensor from %s [%s] - %s",
                dev.friendly_name,
                dev.id,
                sensor.key,
            )
            is_numeric = (
                sensor.device_class not in sensor_const.NON_NUMERIC_DEVICE_CLASSES
            )
            ha_entity = HubSpaceSensor(coordinator_hubspace, sensor, dev, is_numeric)
            entities.append(ha_entity)
    async_add_entities(entities)
