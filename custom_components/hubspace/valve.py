"""Home Assistant entity for interacting with Afero Valves."""

from functools import partial

from aioafero.v1 import AferoBridgeV1
from aioafero.v1.controllers.event import EventType
from aioafero.v1.controllers.valve import ValveController
from aioafero.v1.models.valve import Valve
from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN
from .entity import HubspaceBaseEntity


class HubspaceValve(HubspaceBaseEntity, ValveEntity):
    """Representation of an Afero valve."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: ValveController,
        resource: Valve,
        instance: str,
    ) -> None:
        """Initialize an Afero Valve."""
        super().__init__(
            bridge,
            controller,
            resource,
            instance=instance,
        )
        self.instance = instance

    @property
    def supported_features(self) -> ValveEntityFeature:
        """Determines if the Valve can be Open or Closed.

        Afero valves always report this information
        """
        return ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    @property
    def reports_position(self) -> bool:
        """Determines if the Valve reports its position."""
        return self.resource.open.get(self.instance) is not None

    @property
    def current_valve_position(self) -> int | None:
        """Current position of the valve.

        Afero only reports Open / Close so default to 100 or 0
        """
        feature = self.resource.open.get(self.instance)
        if feature:
            return 100 if feature.open else 0
        return None

    async def async_open_valve(self, **kwargs) -> None:
        """Open the valve."""
        self.logger.info("Opening valve on %s", self._attr_name)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            valve_open=True,
            instance=self.instance,
        )

    async def async_close_valve(self, **kwargs) -> None:
        """Close valve."""
        self.logger.info("Closing valve on %s", self._attr_name)
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            valve_open=False,
            instance=self.instance,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]
    api: AferoBridgeV1 = bridge.api
    controller: ValveController = api.valves
    make_entity = partial(HubspaceValve, bridge, controller)

    def get_unique_entities(hs_resource: Valve) -> list[HubspaceValve]:
        instances = hs_resource.open.keys()
        return [
            make_entity(hs_resource, instance)
            for instance in instances
            if len(instances) == 1 or instance is not None
        ]

    @callback
    def async_add_entity(event_type: EventType, hs_resource: Valve) -> None:
        """Add an entity."""
        async_add_entities(get_unique_entities(hs_resource))

    # add all current items in controller
    entities: list[HubspaceValve] = []
    for resource in controller:
        entities.extend(get_unique_entities(resource))
    async_add_entities(entities)
    # register listener for new entities
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=EventType.RESOURCE_ADDED)
    )
