import logging
from typing import Optional

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_VALVE
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


class HubSpaceValve(HubSpaceEntity, ValveEntity):
    """HubSpace switch-type that can communicate with Home Assistant

    :ivar _current_valve_position: Current position of the valve
    :ivar _instance: functionInstance within the HS device
    :ivar _reports_position: Reports position of the valve
    :ivar _state: If the device is on / off
    """

    ENTITY_TYPE = ENTITY_VALVE

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        device: HubSpaceDevice,
        instance: Optional[str],
    ) -> None:
        # Assume that all HubSpace devices allow for open / close
        self._supported_features: ValveEntityFeature = (
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )
        self._state: Optional[str] = None
        self._instance = instance
        self._current_valve_position: int | None = None
        self._reports_position: bool = True
        super().__init__(coordinator, device)

    def update_states(self) -> None:
        """Load initial states into the device"""
        for state in self.get_device_states():
            if state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass != "toggle":
                continue
            if not self._instance or state.functionInstance == self._instance:
                self._state = state.value

    @property
    def supported_features(self) -> ValveEntityFeature:
        return self._supported_features

    @property
    def reports_position(self) -> bool:
        """Return true if device is on."""
        return self._reports_position

    @property
    def current_valve_position(self) -> Optional[int]:
        return 100 if self._state == "on" else 0

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
            entity,
            instance=instance,
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
        entity,
        instance=None,
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
