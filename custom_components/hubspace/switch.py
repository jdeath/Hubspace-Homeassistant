import logging
from typing import Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hubspace_async import HubSpaceDevice, HubSpaceState

from . import HubSpaceConfigEntry
from .const import DOMAIN, ENTITY_SWITCH
from .coordinator import HubSpaceDataUpdateCoordinator
from .hubspace_entity import HubSpaceEntity

_LOGGER = logging.getLogger(__name__)


class HubSpaceSwitch(HubSpaceEntity, SwitchEntity):
    """HubSpace switch-type that can communicate with Home Assistant

    :ivar _instance: functionInstance within the HS device
    :ivar _state: Current state of the switch
    """

    ENTITY_TYPE = ENTITY_SWITCH

    def __init__(
        self,
        coordinator: HubSpaceDataUpdateCoordinator,
        device: HubSpaceDevice,
        instance: Optional[str],
    ) -> None:
        self._instance: Optional[str] = instance
        self._state: Optional[str] = None
        super().__init__(coordinator, device)

    def update_states(self) -> None:
        """Load initial states into the device"""
        for state in self.get_device_states():
            if state.functionClass == "available":
                self._availability = state.value
            elif state.functionClass != self.primary_class:
                continue
            elif not self._instance or state.functionInstance == self._instance:
                self._state = state.value

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if self._state is None:
            return None
        else:
            return self._state == "on"

    @property
    def primary_class(self) -> str:
        return "toggle" if self._instance else "power"

    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.debug("Enabling %s on %s", self._instance, self._child_id)
        self._state = "on"
        states_to_set = [
            HubSpaceState(
                functionClass=self.primary_class,
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
    entity: HubSpaceDevice,
) -> list[HubSpaceSwitch]:
    valid: list[HubSpaceSwitch] = []
    for function in entity.functions:
        if function["functionClass"] != "toggle":
            continue
        instance = function["functionInstance"]
        _LOGGER.debug("Adding a %s [%s] @ %s", entity.device_class, entity.id, instance)
        ha_entity = HubSpaceSwitch(
            coordinator_hubspace,
            entity,
            instance=instance,
        )
        valid.append(ha_entity)
    return valid


async def setup_basic_switch(
    coordinator_hubspace: HubSpaceDataUpdateCoordinator,
    entity: HubSpaceDevice,
):
    _LOGGER.debug("No toggleable elements found. Setting up as a basic switch")
    ha_entity = HubSpaceSwitch(
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
    """Add Switch entities from a config_entry."""
    coordinator_hubspace: HubSpaceDataUpdateCoordinator = (
        entry.runtime_data.coordinator_hubspace
    )
    device_registry = dr.async_get(hass)
    entities: list[HubSpaceSwitch] = []
    for entity in coordinator_hubspace.data[ENTITY_SWITCH].values():
        _LOGGER.debug("Processing a %s, %s", entity.device_class, entity.id)
        new_devs = await setup_entry_toggled(
            coordinator_hubspace,
            entity,
        )
        if new_devs:
            entities.extend(new_devs)
        else:
            entities.append(
                await setup_basic_switch(
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
