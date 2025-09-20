"""Home Assistant entity for interacting with Afero security-system."""

from functools import partial

from aioafero.v1 import AferoBridgeV1, SecuritySystemController
from aioafero.v1.controllers.event import EventType
from aioafero.v1.models import SecuritySystem
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class HubspaceSecuritySystem(HubspaceBaseEntity, AlarmControlPanelEntity):
    """Representation of an Afero Security System."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: SecuritySystemController,
        resource: SecuritySystem,
    ) -> None:
        """Initialize an Afero Security System."""

        super().__init__(bridge, controller, resource)
        self._supported_features: AlarmControlPanelEntityFeature = (
            AlarmControlPanelEntityFeature(0)
        )
        if resource.supports_away:
            self._supported_features += AlarmControlPanelEntityFeature.ARM_AWAY
        if resource.supports_home:
            self._supported_features += AlarmControlPanelEntityFeature.ARM_HOME
        if resource.supports_trigger:
            self._supported_features += AlarmControlPanelEntityFeature.TRIGGER

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Get all supported features."""
        return self._supported_features

    @property
    def code_arm_required(self) -> bool:
        """States if the code is required to arm the system."""
        return False

    @property
    def code_format(self) -> CodeFormat | None:
        """Format for PIN."""
        return CodeFormat.NUMBER

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self.bridge.async_request_call(
            self.controller.disarm,
            device_id=self.resource.id,
            disarm_pin=code,
        )

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self.bridge.async_request_call(
            self.controller.arm_home,
            device_id=self.resource.id,
        )

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self.bridge.async_request_call(
            self.controller.arm_away,
            device_id=self.resource.id,
        )

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""
        await self.bridge.async_request_call(
            self.controller.alarm_trigger,
            device_id=self.resource.id,
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current state of the system."""
        mapping = {
            "arm-away": AlarmControlPanelState.ARMED_AWAY,
            "alarming": AlarmControlPanelState.TRIGGERED,
            "alarming-sos": AlarmControlPanelState.TRIGGERED,
            "arm-stay": AlarmControlPanelState.ARMED_HOME,
            "arm-started-stay": AlarmControlPanelState.ARMING,
            "disarmed": AlarmControlPanelState.DISARMED,
            "triggered": AlarmControlPanelState.PENDING,
            "arm-started-away": AlarmControlPanelState.ARMING,
        }
        return mapping.get(self.resource.alarm_state.mode)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: SecuritySystemController = api.security_systems
    make_entity = partial(HubspaceSecuritySystem, bridge, controller)

    @callback
    def async_add_entity(event_type: EventType, resource: SecuritySystem) -> None:
        """Add an entity."""
        async_add_entities([make_entity(resource)])

    # add all current items in controller
    async_add_entities([make_entity(entity) for entity in controller])
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
