import logging
from typing import Optional

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_LOCK
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceLock(LockEntity):
    """HubSpace lock that can communicate with Home Assistant

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _current_position: Current position of the device (right [locked], left [unlocked])
    """

    def __init__(
        self,
        hs: HubSpaceDataUpdateCoordinator,
        friendly_name: str,
        child_id: Optional[str] = None,
        model: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        self._name: str = friendly_name
        self.coordinator = hs
        self._hs = hs.conn
        self._child_id: str = child_id
        self._bonus_attrs = {
            "model": model,
            "deviceId": device_id,
            "Child ID": self._child_id,
        }
        # Entity-specific
        self._current_position: Optional[str] = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    def update_states(self) -> None:
        """Load initial states into the device"""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_LOCK][
            self._child_id
        ].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._child_id
            )
        # functionClass -> internal attribute
        for state in states:
            if state.functionClass == "lock-direction":
                self._current_position = state.value

    @property
    def should_poll(self):
        return False

    @property
    def name(self) -> str:
        """Return the display name"""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the HubSpace ID"""
        return self._child_id

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._bonus_attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._bonus_attrs["deviceId"])},
            name=self._name,
            model=self._bonus_attrs["model"],
        )

    @property
    def supported_features(self) -> LockEntityFeature:
        # Is open the same as unlock?
        # https://developers.home-assistant.io/docs/core/entity/lock/#unlock
        return LockEntityFeature.OPEN

    @property
    def is_locked(self) -> bool:
        return self._current_position == "right"

    @property
    def is_open(self) -> bool:
        return self._current_position != "right"

    async def async_unlock(self, **kwargs) -> None:
        _LOGGER.debug("Unlocking %s [%s]", self._name, self._child_id)
        self._current_position = "left"
        states_to_set = [
            HubSpaceState(
                functionClass="lock-direction",
                functionInstance=self._current_position,
                value=self._current_position,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()

    async def async_lock(self, **kwargs) -> None:
        _LOGGER.debug("Locking %s [%s]", self._name, self._child_id)
        self._current_position = "right"
        states_to_set = [
            HubSpaceState(
                functionClass="lock-direction",
                functionInstance=self._current_position,
                value=self._current_position,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Fan entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    entities: list[HubSpaceLock] = []
    device_registry = dr.async_get(hass)
    for entity in coordinator_hubspace.data[ENTITY_LOCK].values():
        _LOGGER.debug("Adding a %s, %s", entity.device_class, entity.friendly_name)
        ha_entity = HubSpaceLock(
            coordinator_hubspace,
            entity.friendly_name,
            child_id=entity.id,
            model=entity.model,
            device_id=entity.device_id,
        )
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
        )
        entities.append(ha_entity)
    async_add_entities(entities)
