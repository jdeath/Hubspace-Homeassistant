"""The HubSpace coordinator."""

import json
import logging
import os
from asyncio import timeout
from collections import defaultdict
from datetime import timedelta
from typing import Any, NewType, Union

import aiofiles
import hubspace_async
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import anonomyize_data, const, discovery

_LOGGER = logging.getLogger(__name__)
_LOGGER_HS = logging.getLogger(hubspace_async.__name__)

coordinator_data = NewType(
    "coordinator_data", dict[str, dict[str, Union[hubspace_async.HubSpaceDevice, dict]]]
)


class HubSpaceDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        conn: hubspace_async.HubSpaceConnection,
        timeout: int,
        friendly_names: list[str],
        room_names: list[str],
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.conn = conn
        self.timeout = timeout
        self.tracked_devices: list[hubspace_async.HubSpaceDevice] = []
        self.states: dict[str, list[hubspace_async.HubSpaceState]] = {}
        self.friendly_names = friendly_names
        self.room_names = room_names
        # We only want to perform the sensor checks once per device
        # to reduce the same computing
        self.sensors: dict[str, defaultdict] = {
            const.ENTITY_BINARY_SENSOR: defaultdict(dict),
            const.ENTITY_SENSOR: defaultdict(dict),
        }
        self._sensor_checks: list[str] = []
        # HubSpace loves to duplicate data across multiple devices, and
        # we only want to add it once
        self._added_sensors: list[str] = []

        super().__init__(
            hass,
            _LOGGER,
            name=const.DOMAIN,
            update_interval=update_interval,
        )

    async def process_sensor_devs(self, dev: hubspace_async.HubSpaceDevice):
        """Get sensors from a device"""
        if dev.id not in self._sensor_checks:
            _LOGGER.debug(
                "Performing sensor checks for device %s [%s]", dev.friendly_name, dev.id
            )
            self._sensor_checks.append(dev.id)
            # sensors
            if sensors := await get_sensors(dev):
                self.sensors[const.ENTITY_SENSOR][dev.id] = (
                    await self.process_sensor_dev(dev, sensors)
                )
            # binary sensors
            if sensors := await get_binary_sensors(dev):
                self.sensors[const.ENTITY_BINARY_SENSOR][dev.id] = (
                    await self.process_sensor_dev(dev, sensors)
                )

    async def process_sensor_dev(
        self, dev: hubspace_async.HubSpaceDevice, sensors: list
    ) -> list:
        de_duped = []
        for sensor in sensors:
            if dev.device_id:
                unique = f"{dev.device_id}_{sensor.key}"
            else:
                unique = f"{dev.id}_{sensor.key}"
            if unique not in self._added_sensors:
                self._added_sensors.append(unique)
                de_duped.append(sensor)
        return de_duped

    async def _async_update_data(
        self,
    ) -> coordinator_data:
        """Update data via library."""
        # Update the hubspace_async logger to match our logger
        _LOGGER_HS.setLevel(_LOGGER.getEffectiveLevel())
        await self.hs_data_update()
        if _LOGGER.getEffectiveLevel() <= logging.DEBUG:
            data = await anonomyize_data.generate_anon_data(self.conn)
            curr_directory = os.path.dirname(os.path.realpath(__file__))
            dev_dump = os.path.join(curr_directory, "_dump_hs_devices.json")
            _LOGGER.debug("Writing out anonymized device data to %s", dev_dump)
            async with aiofiles.open(dev_dump, "w") as fh:
                await fh.write(json.dumps(data, indent=4))
            dev_raw = os.path.join(curr_directory, "_dump_hs_raw.json")
            _LOGGER.debug("Writing out raw device data to %s", dev_raw)
            async with aiofiles.open(dev_raw, "w") as fh:
                await fh.write(json.dumps(self.conn.raw_devices, indent=4))
        return await self.process_tracked_devices()

    async def hs_data_update(self) -> None:
        """Update the data via library."""
        try:
            async with timeout(self.timeout):
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
            await self.process_sensor_devs(dev)
            if dev.id in self.sensors[const.ENTITY_SENSOR]:
                devices[const.ENTITY_SENSOR][dev.id] = {
                    "device": dev,
                    "sensors": self.sensors[const.ENTITY_SENSOR][dev.id],
                }
            if dev.id in self.sensors[const.ENTITY_BINARY_SENSOR]:
                devices[const.ENTITY_BINARY_SENSOR][dev.id] = {
                    "device": dev,
                    "sensors": self.sensors[const.ENTITY_BINARY_SENSOR][dev.id],
                }
        return devices


async def get_sensors(
    dev: hubspace_async.HubSpaceDevice,
) -> list[SensorEntityDescription]:
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


async def get_binary_sensors(
    dev: hubspace_async.HubSpaceDevice,
) -> list[BinarySensorEntityDescription]:
    required_sensors: list[BinarySensorEntityDescription] = []
    binary_sensors = const.BINARY_SENSORS.get(dev.device_class, {})
    for state in dev.states:
        key = state.functionClass
        if state.functionInstance:
            key += f"|{state.functionInstance}"
        if key in binary_sensors:
            required_sensors.append(binary_sensors[key])
            _LOGGER.debug(
                "Found a binary sensor, %s, attached to %s [%s]",
                key,
                dev.friendly_name,
                dev.id,
            )
    return required_sensors


async def create_devices_from_data(
    file_name: str,
) -> list[hubspace_async.HubSpaceDevice]:
    """Generate devices from a data dump

    :param file_name: Name of the file to load
    """
    current_path: str = os.path.dirname(os.path.realpath(__file__))
    async with aiofiles.open(os.path.join(current_path, file_name), "r") as fh:
        data = await fh.read()
    devices = json.loads(data)
    processed = []
    for device in devices:
        processed_states = []
        for state in device["states"]:
            processed_states.append(hubspace_async.HubSpaceState(**state))
        device["states"] = processed_states
        if "children" not in device:
            device["children"] = []
        processed.append(hubspace_async.HubSpaceDevice(**device))
    return processed
