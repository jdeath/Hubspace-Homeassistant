import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor import const as sensor_const
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_SENSOR
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceSensor(CoordinatorEntity, SensorEntity):
    """HubSpace child sensor component"""

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        description: SensorEntityDescription,
        device: HubSpaceDevice,
        is_numeric: bool,
    ) -> None:
        super().__init__(coordinator, context=device.id)
        self.coordinator = coordinator
        self.entity_description = description
        self._device = device
        self._is_numeric: bool = is_numeric
        self._sensor_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    def update_states(self) -> None:
        """Handle updated data from the coordinator."""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_SENSOR][
            self._device.id
        ]["device"].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._device.id
            )
        for state in states:
            if state.functionClass == self.entity_description.key:
                if self._is_numeric and isinstance(state.value, str):
                    state.value = int("".join(i for i in state.value if i.isdigit()))
                self._sensor_value = state.value

    @property
    def unique_id(self) -> str:
        return f"{self._device.id}_{self.entity_description.key}"

    @property
    def name(self) -> str:
        return f"{self._device.friendly_name}: {self.entity_description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        model = self._device.model if self._device.model != "TBD" else None
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            name=self._device.friendly_name,
            model=model,
        )

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
