"""Home Assistant entity for interacting with Afero lock."""

from functools import partial

from aioafero.v1 import AferoBridgeV1
from aioafero.v1.controllers.event import EventType
from aioafero.v1.controllers.lock import LockController, features
from aioafero.v1.models.lock import Lock
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity, update_decorator


class HubspaceLock(HubspaceBaseEntity, LockEntity):
    """Representation of an Afero lock."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: LockController,
        resource: Lock,
    ) -> None:
        """Initialize an Afero lock."""

        super().__init__(bridge, controller, resource)
        self._supported_features: LockEntityFeature = LockEntityFeature(
            LockEntityFeature.OPEN
        )

    @property
    def supported_features(self) -> LockEntityFeature:
        """States what features are supported by the lock."""
        return self._supported_features

    @property
    def is_locked(self) -> bool:
        """Indication of whether the lock is currently locked."""
        return self.resource.position.position == features.CurrentPositionEnum.LOCKED

    @property
    def is_locking(self) -> bool:
        """Indication of whether the lock is currently locking."""
        return self.resource.position.position == features.CurrentPositionEnum.LOCKING

    @property
    def is_unlocking(self) -> bool:
        """Indication of whether the lock is currently unlocking."""
        return self.resource.position.position == features.CurrentPositionEnum.UNLOCKING

    @property
    def is_opening(self) -> bool:
        """Indication of whether the lock is currently opening."""
        return self.resource.position.position == features.CurrentPositionEnum.UNLOCKING

    @property
    def is_open(self) -> bool:
        """Indication of whether the lock is currently open."""
        return self.resource.position.position == features.CurrentPositionEnum.UNLOCKED

    @update_decorator
    async def async_unlock(self, **kwargs) -> None:
        """Unlock all or specified locks."""
        self.logger.info("Unlocking %s [%s]", self.name, self.resource.id)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            lock_position=features.CurrentPositionEnum.UNLOCKING,
        )

    @update_decorator
    async def async_lock(self, **kwargs) -> None:
        """Lock all or specified locks."""
        self.logger.info("Unlocking %s [%s]", self.name, self.resource.id)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            lock_position=features.CurrentPositionEnum.LOCKING,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: LockController = api.locks
    make_entity = partial(HubspaceLock, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: Lock) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities([make_entity(entity) for entity in controller])
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
