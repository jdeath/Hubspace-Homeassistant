import logging
from typing import Optional

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_LOCK
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


class HubSpaceLock(HubSpaceEntity, LockEntity):
    """HubSpace lock that can communicate with Home Assistant

    :ivar _current_position: Current position of the device
    :ivar _supported_features: Supported features of the device
    """

    ENTITY_TYPE = ENTITY_LOCK

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        device: HubSpaceDevice,
    ) -> None:
        self._current_position: Optional[str] = None
        self._supported_features: Optional[LockEntityFeature] = LockEntityFeature(0)
        super().__init__(coordinator, device)

    def process_functions(self, functions: list[dict]) -> None:
        """Process available functions

        :param functions: Functions that are supported from the API
        """
        for function in functions:
            if function["functionClass"] == "lock-control":
                _LOGGER.debug("Found lock-control. Determining open state support")
                for value in function["values"]:
                    if value["name"] == "unlocked":
                        self._supported_features |= LockEntityFeature.OPEN

    def update_states(self) -> None:
        """Load initial states into the device"""
        for state in self.get_device_states():
            if state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass == "lock-control":
                _LOGGER.debug("Found lock-control and setting to %s", state.value)
                self._current_position = state.value

    @property
    def supported_features(self) -> LockEntityFeature:
        return self._supported_features

    @property
    def is_locked(self) -> bool:
        return self._current_position == "locked"

    @property
    def is_locking(self) -> bool:
        return self._current_position == "locking"

    @property
    def is_unlocking(self) -> bool:
        return self._current_position == "unlocking"

    @property
    def is_opening(self) -> bool:
        return self._current_position == "unlocking"

    @property
    def is_open(self) -> bool:
        return self._current_position == "unlocked"

    async def async_unlock(self, **kwargs) -> None:
        _LOGGER.debug("Unlocking %s [%s]", self.name, self._child_id)
        self._current_position = "unlocking"
        states_to_set = [
            HubSpaceState(
                functionClass="lock-control",
                functionInstance=None,
                value=self._current_position,
            )
        ]
        await self.set_device_states(states_to_set)
        self.async_write_ha_state()

    async def async_lock(self, **kwargs) -> None:
        _LOGGER.debug("Locking %s [%s]", self.name, self._child_id)
        self._current_position = "locking"
        states_to_set = [
            HubSpaceState(
                functionClass="lock-control",
                functionInstance=None,
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
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
            manufacturer=entity.manufacturerName,
        )
        ha_entity = HubSpaceLock(coordinator_hubspace, entity)
        entities.append(ha_entity)
    async_add_entities(entities)
