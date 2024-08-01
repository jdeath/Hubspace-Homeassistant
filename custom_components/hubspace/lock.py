import logging
from typing import Optional

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from hubspace_async import HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_LOCK
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceLock(CoordinatorEntity, LockEntity):
    """HubSpace lock that can communicate with Home Assistant

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _current_position: Current position of the device
    :ivar _supported_features: Supported features of the device
    :ivar _availability: If the device is available within HubSpace
    """

    def __init__(
        self,
        hs: HubSpaceDataUpdateCoordinator,
        friendly_name: str,
        child_id: Optional[str] = None,
        model: Optional[str] = None,
        device_id: Optional[str] = None,
        functions: Optional[list] = None,
    ) -> None:
        super().__init__(hs, context=child_id)
        self._name: str = friendly_name
        self.coordinator = hs
        self._hs = hs.conn
        self._child_id: str = child_id
        self._bonus_attrs = {
            "model": model,
            "deviceId": device_id,
            "Child ID": self._child_id,
        }
        self._availability: Optional[bool] = None
        # Entity-specific
        self._current_position: Optional[str] = None
        self._supported_features: Optional[LockEntityFeature] = LockEntityFeature(0)
        functions = functions or []
        self.process_functions(functions)

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
        _LOGGER.debug("About to update using %s", states)
        # functionClass -> internal attribute
        for state in states:
            if state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass == "lock-control":
                _LOGGER.debug("Found lock-control and setting to %s", state.value)
                self._current_position = state.value

    @property
    def name(self) -> str:
        """Return the display name"""
        return self._name

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
            name=self._name,
            model=model,
        )

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
        _LOGGER.debug("Unlocking %s [%s]", self._name, self._child_id)
        self._current_position = "unlocking"
        states_to_set = [
            HubSpaceState(
                functionClass="lock-control",
                functionInstance=None,
                value=self._current_position,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()

    async def async_lock(self, **kwargs) -> None:
        _LOGGER.debug("Locking %s [%s]", self._name, self._child_id)
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
        ha_entity = HubSpaceLock(
            coordinator_hubspace,
            entity.friendly_name,
            child_id=entity.id,
            model=entity.model,
            device_id=entity.device_id,
            functions=entity.functions,
        )
        entities.append(ha_entity)
    async_add_entities(entities)
