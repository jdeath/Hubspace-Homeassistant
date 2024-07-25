import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_SENSOR
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceSensor(SensorEntity):
    """HubSpace child sensor component"""

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        description: SensorEntityDescription,
        device: HubSpaceDevice,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._device = device
        self._sensor_value = None

    @property
    def unique_id(self) -> str:
        return f"{self._device.id}_{self.entity_description.key}"

    @property
    def name(self) -> str:
        return f"{self.entity_description.key}"

    async def async_update(self) -> None:
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
                self._sensor_value = state.value

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
            ha_entity = HubSpaceSensor(coordinator_hubspace, sensor, dev)
            entities.append(ha_entity)
    async_add_entities(entities)
