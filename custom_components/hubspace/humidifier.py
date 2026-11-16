"""Home Assistant entity for interacting with Afero humidifiers and dehumidifiers."""

from functools import partial
from typing import Any

from aioafero.v1 import AferoBridgeV1, DehumidifierController, HumidifierController
from aioafero.v1.controllers.event import EventType
from aioafero.v1.models import Dehumidifier, Humidifier
from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class HubspaceDehumidifier(HubspaceBaseEntity, HumidifierEntity):
    """Representation of an Afero dehumidifier."""

    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: DehumidifierController | HumidifierController,
        resource: Dehumidifier | Humidifier,
    ) -> None:
        """Initialize an Afero humidifier or dehumidifier."""
        super().__init__(bridge, controller, resource)
        if self.resource.mode:
            self._attr_supported_features = HumidifierEntityFeature.MODES
        if self.resource.target_humidity:
            self._attr_target_humidity_step = self.resource.target_humidity.step

    @property
    def is_on(self) -> bool | None:
        """Return whether the dehumidifier is powered on."""
        return self.resource.on.on if self.resource.on else None

    @property
    def current_humidity(self) -> int | None:
        """Return the measured relative humidity."""
        return self.resource.current_humidity

    @property
    def target_humidity(self) -> int | None:
        """Return the relative humidity the unit is trying to reach."""
        target = self.resource.target_humidity
        return target.value if target else None

    @property
    def min_humidity(self) -> float:
        """Return the lowest settable target humidity."""
        target = self.resource.target_humidity
        return target.min if target else super().min_humidity

    @property
    def max_humidity(self) -> float:
        """Return the highest settable target humidity."""
        target = self.resource.target_humidity
        return target.max if target else super().max_humidity

    @property
    def mode(self) -> str | None:
        """Return the active mode."""
        return self.resource.mode.mode if self.resource.mode else None

    @property
    def available_modes(self) -> list[str] | None:
        """Return all modes the unit supports."""
        return sorted(self.resource.mode.modes) if self.resource.mode else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dehumidifier on."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, on=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dehumidifier off."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, on=False
        )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set a new target humidity, snapped to the unit's step and range."""
        if (target := self.resource.target_humidity) is None:
            raise ServiceValidationError("Device does not report a target humidity")
        snapped = (
            target.min + round((humidity - target.min) / target.step) * target.step
        )
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            target_humidity=int(min(max(snapped, target.min), target.max)),
        )

    async def async_set_mode(self, mode: str) -> None:
        """Set a new mode."""
        await self.bridge.async_request_call(
            self.controller.set_state, device_id=self.resource.id, mode=mode
        )


class HubspaceHumidifier(HubspaceDehumidifier):
    """Representation of an Afero humidifier.

    The target humidity is only used by the unit while it is in ``auto`` mode.
    """

    _attr_device_class = HumidifierDeviceClass.HUMIDIFIER
    _attr_translation_key = "humidifier"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    for controller, entity_cls in (
        (api.dehumidifiers, HubspaceDehumidifier),
        (api.humidifiers, HubspaceHumidifier),
    ):
        setup_controller(
            config_entry, async_add_entities, partial(entity_cls, bridge, controller)
        )


def setup_controller(
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    make_entity: partial,
) -> None:
    """Add a controller's current entities and listen for new ones."""
    controller: DehumidifierController | HumidifierController = make_entity.args[1]

    @callback
    def async_add_entity(
        event_type: EventType, resource: Dehumidifier | Humidifier
    ) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities(make_entity(entity) for entity in controller)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
