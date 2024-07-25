"""The HubSpace coordinator."""

import json
import logging
from asyncio import timeout
from collections import defaultdict
from datetime import timedelta
from typing import Any, NewType, Union

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from hubspace_async import HubSpaceConnection, HubSpaceDevice, HubSpaceState

from . import anonomyize_data, const, discovery

_LOGGER = logging.getLogger(__name__)

coordinator_data = NewType(
    "coordinator_data", dict[str, dict[str, Union[HubSpaceDevice, dict]]]
)


class HubSpaceDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        conn: HubSpaceConnection,
        friendly_names: list[str],
        room_names: list[str],
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.conn = conn
        self.tracked_devices: list[HubSpaceDevice] = []
        self.states: dict[str, list[HubSpaceState]] = {}
        self.friendly_names = friendly_names
        self.room_names = room_names
        # We only want to perform the sensor checks once per device
        # to reduce the same computing
        self.sensors: defaultdict[str, list] = defaultdict(list)
        self._sensor_checks: list[str] = []
        # HubSpace loves to duplicate data across multiple devices and
        # we only want to add it once
        self._added_sensors: list[str] = []

        super().__init__(
            hass,
            _LOGGER,
            name="hubspace",
            update_interval=update_interval,
        )

    async def process_sensor_devs(self, dev: HubSpaceDevice) -> list:
        """Get sensors from a device"""
        if dev.id not in self._sensor_checks:
            _LOGGER.debug(
                "Performing sensor checks for device %s [%s]", dev.friendly_name, dev.id
            )
            self._sensor_checks.append(dev.id)

            if sensors := await get_sensors(dev):
                de_duped_sensors = []
                for sensor in sensors:
                    if dev.device_id:
                        unique = f"{dev.device_id}_{sensor.key}"
                    else:
                        unique = f"{dev.id}_{sensor.key}"
                    if unique not in self._added_sensors:
                        self._added_sensors.append(unique)
                        de_duped_sensors.append(sensor)
                self.sensors[dev.id] = de_duped_sensors
        return self.sensors[dev.id]

    async def _async_update_data(
        self,
    ) -> coordinator_data:
        """Update data via library."""
        await self.hs_data_update()
        if _LOGGER.getEffectiveLevel() <= logging.DEBUG:
            data = await anonomyize_data.generate_anon_data(self.conn)
            _LOGGER.debug(json.dumps(data, indent=4))
        return await self.process_tracked_devices()

    async def hs_data_update(self) -> None:
        """Update the data via library."""
        try:
            async with timeout(10):
                await self.conn.populate_data()
        except Exception as error:
            raise UpdateFailed(error) from error
        self.tracked_devices = await discovery.get_requested_devices(
            self.conn, self.friendly_names, self.room_names
        )

    async def process_tracked_devices(
        self,
    ) -> coordinator_data:
        """Process the populated devices

        Sort the devices into their entity types and add sensors where required
        """
        devices: coordinator_data = defaultdict(dict)
        for dev in self.tracked_devices:
            if dev.children:
                _LOGGER.debug(
                    "Skipping %s [%s] as it has children", dev.friendly_name, dev.id
                )
                continue
            mapped = const.DEVICE_CLASS_TO_ENTITY_MAP.get(dev.device_class)
            if not mapped:
                if dev.device_class not in const.UNMAPPED_DEVICE_CLASSES:
                    _LOGGER.warning(
                        "Found an unmapped device_class, %s", dev.device_class
                    )
                else:
                    _LOGGER.info(
                        "Found a known unmapped device_class, %s", dev.device_class
                    )
                continue
            _LOGGER.debug("Adding device %s to %s", dev.friendly_name, mapped)
            devices[mapped][dev.id] = dev
            if dev_sensors := await self.process_sensor_devs(dev):
                devices[const.ENTITY_SENSOR][dev.id] = {
                    "device": dev,
                    "sensors": dev_sensors,
                }
        return devices


async def get_sensors(dev: HubSpaceDevice) -> list[SensorEntityDescription]:
    """Get sensors from a device"""
    required_sensors: list[SensorEntityDescription] = []
    for state in dev.states:
        sensor = const.SENSORS_GENERAL.get(state.functionClass)
        if not sensor:
            continue
        _LOGGER.debug(
            "Found a sensor, %s, attached to %s [%s]",
            state.functionClass,
            dev.friendly_name,
            dev.id,
        )
        required_sensors.append(sensor)
    return required_sensors
