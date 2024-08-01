import logging
from typing import Optional

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_VALVE
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceValve(CoordinatorEntity, ValveEntity):
    """HubSpace switch-type that can communicate with Home Assistant

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _state: If the device is on / off
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _availability: If the device is available within HubSpace
    :ivar _instance: functionInstance within the HS device
    :ivar _current_valve_position: Current position of the valve
    :ivar _reports_position: Reports position of the valve
    """

    def __init__(
        self,
        hs: HubSpaceDataUpdateCoordinator,
        friendly_name: str,
        instance: Optional[str],
        child_id: Optional[str] = None,
        model: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        super().__init__(hs, context=child_id)
        self._name: str = friendly_name
        self.coordinator = hs
        self._hs = hs.conn
        self._child_id: str = child_id
        self._state: Optional[str] = None
        self._bonus_attrs = {
            "model": model,
            "deviceId": device_id,
            "Child ID": self._child_id,
        }
        self._availability: Optional[bool] = None
        # Entity-specific
        # Assume that all HubSpace devices allow for open / close
        self._supported_features: ValveEntityFeature = (
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )
        self._instance = instance
        self._current_valve_position: int | None = None
        self._reports_position: bool = True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    def update_states(self) -> None:
        """Load initial states into the device"""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_VALVE][
            self._child_id
        ].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._child_id
            )
        # functionClass -> internal attribute
        for state in states:
            if state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass != "toggle":
                continue
            if not self._instance:
                self._state = state.value
            elif state.functionInstance == self._instance:
                self._state = state.value

    @property
    def should_poll(self):
        return False

    @property
    def name(self) -> str:
        """Return the display name"""
        if self._instance:
            return f"{self._name} - {self._instance}"
        else:
            return self._name

    @property
    def unique_id(self) -> str:
        """Return the HubSpace ID"""
        if self._instance:
            return f"{self._child_id}-{self._instance}"
        else:
            return self._child_id

    @property
    def available(self) -> bool:
        return self._availability is True

    @property
    def supported_features(self) -> ValveEntityFeature:
        return self._supported_features

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._bonus_attrs

    @property
    def reports_position(self) -> bool:
        """Return true if device is on."""
        return self._reports_position

    @property
    def current_valve_position(self) -> Optional[int]:
        return 100 if self._state == "on" else 0

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
    def device_class(self) -> ValveDeviceClass:
        return ValveDeviceClass.WATER

    async def async_open_valve(self, **kwargs) -> None:
        _LOGGER.debug("Opening %s on %s", self._instance, self._child_id)
        self._state = "on"
        states_to_set = [
            HubSpaceState(
                functionClass="toggle",
                functionInstance=self._instance,
                value=self._state,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()

    async def async_close_valve(self, **kwargs) -> None:
        _LOGGER.debug("Closing %s on %s", self._instance, self._child_id)
        self._state = "off"
        states_to_set = [
            HubSpaceState(
                functionClass="toggle",
                functionInstance=self._instance,
                value=self._state,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()


async def setup_entry_toggled(
    coordinator_hubspace: HubSpaceDataUpdateCoordinator,
    entity: HubSpaceDevice,
) -> list[HubSpaceValve]:
    valid: list[HubSpaceValve] = []
    for function in entity.functions:
        if function["functionClass"] != "toggle":
            continue
        instance = function["functionInstance"]
        _LOGGER.debug("Adding a %s [%s] @ %s", entity.device_class, entity.id, instance)
        ha_entity = HubSpaceValve(
            coordinator_hubspace,
            entity.friendly_name,
            instance,
            child_id=entity.id,
            model=entity.model,
            device_id=entity.device_id,
        )
        valid.append(ha_entity)
    return valid


async def setup_basic_valve(
    coordinator_hubspace: HubSpaceDataUpdateCoordinator,
    entity: HubSpaceDevice,
):
    _LOGGER.debug("No toggleable elements found. Setting up as a single valve")
    ha_entity = HubSpaceValve(
        coordinator_hubspace,
        entity.friendly_name,
        None,
        child_id=entity.id,
        model=entity.model,
        device_id=entity.device_id,
    )
    return ha_entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Fan entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    entities: list[HubSpaceValve] = []
    device_registry = dr.async_get(hass)
    for entity in coordinator_hubspace.data[ENTITY_VALVE].values():
        _LOGGER.debug("Processing a %s, %s", entity.device_class, entity.id)
        new_devs = await setup_entry_toggled(
            coordinator_hubspace,
            entity,
        )
        if new_devs:
            entities.extend(new_devs)
        else:
            entities.append(
                await setup_basic_valve(
                    coordinator_hubspace,
                    entity,
                )
            )
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entity.device_id)},
            name=entity.friendly_name,
            model=entity.model,
            manufacturer=entity.manufacturerName,
        )
    async_add_entities(entities)
