"""The HubSpace coordinator."""

import logging
from asyncio import timeout
from datetime import timedelta
from typing import Any
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from hubspace_async import HubSpaceConnection, HubSpaceDevice, HubSpaceState

import json

from . import discovery, anonomyize_data
from . import const

_LOGGER = logging.getLogger(__name__)


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

        super().__init__(
            hass,
            _LOGGER,
            name="hubspace",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with timeout(10):
                await self.conn.populate_data()
        except Exception as error:
            raise UpdateFailed(error) from error
        # Force the data to update
        await self.conn.populate_data()
        self.tracked_devs = await discovery.get_requested_devices(
            self.conn, self.friendly_names, self.room_names
        )
        if _LOGGER.getEffectiveLevel() <= logging.DEBUG:
            data = await anonomyize_data.generate_anon_data(self.conn)
            _LOGGER.debug(json.dumps(data, indent=4))
        devices: dict[str, dict[str, HubSpaceDevice]] = defaultdict(dict)
        # Separate the devices by device_class to reduce logging messages
        # during discovery
        for dev in self.tracked_devs:
            if dev.children:
                _LOGGER.debug("Skipping %s [%s] as it has children", dev.friendly_name, dev.id)
                continue
            mapped = const.DEVICE_CLASS_TO_ENTITY_MAP.get(dev.device_class)
            if not mapped:
                if dev.device_class not in const.UNMAPPED_DEVICE_CLASSES:
                    _LOGGER.warning("Found an unmapped device_class, %s", dev.device_class)
                else:
                    _LOGGER.info("Found a known unmapped device_class, %s", dev.device_class)
                continue
            _LOGGER.debug("Adding device %s to %s", dev.friendly_name, mapped)
            devices[mapped][dev.id] = dev
        return devices
