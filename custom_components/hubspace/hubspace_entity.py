__all__ = ["HubSpaceEntity"]

import logging
from typing import List, Optional

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from hubspace_async import HubSpaceDevice, HubSpaceState

from .const import DOMAIN
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceEntity(CoordinatorEntity):
    """Base entity for HubSpace items

    :ivar _availability: If the device is available within HubSpace HS device
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _device: HubSpace Device to represent
    :ivar _hs: HubSpace connector
    :ivar _instance_attrs: Additional attributes that are required when
        POSTing to HubSpace
    """

    ENTITY_TYPE: str = None

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        device: HubSpaceDevice,
    ) -> None:
        super().__init__(coordinator, context=device.friendly_name)
        self._device = device
        self.coordinator = coordinator
        self._hs = coordinator.conn
        self._availability: Optional[bool] = None
        self._bonus_attrs = {
            "model": device.model,
            "deviceId": device.device_id,
            "Child ID": self._child_id,
        }
        self._instance_attrs: dict[str, str] = {}
        functions = device.functions or []
        self.process_functions(functions)

    @property
    def name(self) -> str:
        """Return the display name"""
        return self._device.friendly_name

    @property
    def unique_id(self) -> str:
        """Return the HubSpace ID"""
        return self._child_id

    @property
    def available(self) -> bool:
        return self._availability is True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._bonus_attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        model = (
            self._bonus_attrs["model"] if self._bonus_attrs["model"] != "TBD" else None
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._bonus_attrs["deviceId"])},
            name=self.name,
            model=model,
        )

    @property
    def should_poll(self):
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    @property
    def _child_id(self):
        return self._device.id

    def process_functions(self, functions: list[dict]) -> None:
        """Implemented by the entity"""
        pass

    def update_states(self) -> None:
        """Implemented by the entity"""
        pass

    async def set_device_state(self, state: HubSpaceState) -> None:
        await self.set_device_states([state])

    async def set_device_states(self, states: List[HubSpaceState]) -> None:
        await self._hs.set_device_states(self._child_id, states)

    def get_device(self) -> HubSpaceDevice:
        try:
            device = self.coordinator.data[self.ENTITY_TYPE][self._child_id]
            if isinstance(device, HubSpaceDevice):
                return device
            else:
                # Sensors track in a dict rather than the device
                return device["device"]
        except KeyError:
            _LOGGER.debug(
                "No device found for %s %s.", self.ENTITY_TYPE, self._child_id
            )
            raise

    def get_device_states(self) -> list[HubSpaceState]:
        try:
            return self.get_device().states
        except KeyError:
            _LOGGER.debug(
                "No device found for %s %s. Maybe hasn't polled yet?",
                self.ENTITY_TYPE,
                self._child_id,
            )
            return []
