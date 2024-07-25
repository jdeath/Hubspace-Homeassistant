import logging
from typing import Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_SWITCH
from .coordinator import HubSpaceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HubSpaceSwitch(SwitchEntity):
    """HubSpace switch-type that can communicate with Home Assistant

    :ivar _name: Name of the device
    :ivar _hs: HubSpace connector
    :ivar _child_id: ID used when making requests to HubSpace
    :ivar _state: If the device is on / off
    :ivar _bonus_attrs: Attributes relayed to Home Assistant that do not need to be
        tracked in their own class variables
    :ivar _device_class: Device class used during lookup
    :ivar _instance: functionInstance within the HS device
    """

    def __init__(
        self,
        hs: HubSpaceDataUpdateCoordinator,
        friendly_name: str,
        instance: Optional[str],
        device_class: str,
        child_id: Optional[str] = None,
        model: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
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
        # Entity-specific
        self._device_class = device_class
        self._instance = instance
        super().__init__(hs, context=self._child_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_states()
        self.async_write_ha_state()

    def update_states(self) -> None:
        """Load initial states into the device"""
        states: list[HubSpaceState] = self.coordinator.data[ENTITY_SWITCH][
            self._child_id
        ].states
        if not states:
            _LOGGER.debug(
                "No states found for %s. Maybe hasn't polled yet?", self._child_id
            )
        # functionClass -> internal attribute
        for state in states:
            if self._instance:
                if state.functionInstance == self._instance:
                    self._state = state.value
            else:
                if state.functionClass == "power":
                    self._state = state.value

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
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

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

    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.debug("Enabling %s on %s", self._instance, self._child_id)
        self._state = "on"
        states_to_set = [
            HubSpaceState(
                functionClass="toggle" if self._instance else "power",
                functionInstance=self._instance,
                value=self._state,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.debug("Disabling %s on %s", self._instance, self._child_id)
        self._state = "off"
        states_to_set = [
            HubSpaceState(
                functionClass="toggle" if self._instance else "power",
                functionInstance=self._instance,
                value=self._state,
            )
        ]
        await self._hs.set_device_states(self._child_id, states_to_set)
        self.async_write_ha_state()


async def setup_entry_toggled(
    coordinator_hubspace: HubSpaceDataUpdateCoordinator,
    registry: dr.DeviceRegistry,
    devices: list[HubSpaceDevice],
    entry: HubSpaceConfigEntry,
) -> list[HubSpaceSwitch]:
    valid: list[HubSpaceSwitch] = []
    for entity in devices:
        _LOGGER.debug("Processing a %s, %s", entity.device_class, entity.id)
        added_dev: bool = False
        for function in entity.functions:
            if function["functionClass"] != "toggle":
                continue
            added_dev = True
            instance = function["functionInstance"]
            _LOGGER.debug(
                "Adding a %s [%s] @ %s", entity.device_class, entity.id, instance
            )
            ha_entity = HubSpaceSwitch(
                coordinator_hubspace,
                entity.friendly_name,
                instance,
                entity.device_class,
                child_id=entity.id,
                model=entity.model,
                device_id=entity.device_id,
            )
            registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, entity.device_id)},
                name=entity.friendly_name,
                model=entity.model,
            )
            valid.append(ha_entity)
        if not added_dev:
            _LOGGER.debug("No toggleable outlets found. Assuming there is only one")
            ha_entity = HubSpaceSwitch(
                coordinator_hubspace,
                entity.friendly_name,
                None,
                entity.device_class,
                child_id=entity.id,
                model=entity.model,
                device_id=entity.device_id,
            )
            registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, entity.device_id)},
                name=entity.friendly_name,
                model=entity.model,
            )
            valid.append(ha_entity)
    return valid


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HubSpaceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Fan entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    device_registry = dr.async_get(hass)
    entities: list[HubSpaceSwitch] = []
    for dev_class in ENTITY_SWITCH:
        entities.extend(
            await setup_entry_toggled(
                coordinator_hubspace,
                device_registry,
                coordinator_hubspace.data[dev_class].values(),
                entry,
            )
        )
    async_add_entities(entities)
