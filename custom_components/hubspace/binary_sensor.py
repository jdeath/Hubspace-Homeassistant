import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_BINARY_SENSOR
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """HubSpace child sensor component"""

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
        device: HubSpaceDevice,
    ) -> None:
        super().__init__(coordinator, context=device.id)
        self.coordinator = coordinator
        self.entity_description = description
        search_data = description.key.split("|", 1)
        self._function_instance = None
        try:
            self._function_class, self._function_instance = search_data
        except ValueError:
            self._function_class = search_data
        self._device = device
        self._sensor_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    def update_states(self) -> None:
        """Handle updated data from the coordinator."""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_BINARY_SENSOR][
            self._device.id
        ]["device"].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._device.id
            )
        for state in states:
            if state.functionClass == self._function_class:
                if (
                    self._function_instance
                    and self._function_instance != state.functionInstance
                ):
                    continue
                self._sensor_value = state.value

    @property
    def unique_id(self) -> str:
        return f"{self._device.id}_{self.entity_description.key}"

    @property
    def name(self) -> str:
        return f"{self._device.friendly_name}: {self.entity_description.name}"

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
