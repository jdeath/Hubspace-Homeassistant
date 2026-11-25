"""Home Assistant entity for interacting with Afero Select."""

from dataclasses import fields

from aioafero import AferoDevice
from aioafero.errors import DeviceNotFound
from aioafero.v1 import AferoController, AferoModelResource
from aioafero.v1.controllers.event import EventType
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HubspaceBridge
from .const import DOMAIN, SELECT_TRANSLATION_KEYS
from .entity import HubspaceBaseEntity


class AferoSelectEntitiy(HubspaceBaseEntity, SelectEntity):
    """Representation of an Afero Select."""

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        identifier: tuple[str, str],
    ) -> None:
        """Initialize an Afero Select."""

        super().__init__(bridge, controller, resource, instance=str(identifier))
        self._identifier: tuple[str, str] = identifier
        self._attr_name = resource.selects[identifier].name
        self._attr_translation_key = SELECT_TRANSLATION_KEYS.get(identifier)

    @property
    def current_option(self) -> str:
        """The current select option."""
        return str(self.resource.selects[self._identifier].selected)

    @property
    def options(self) -> list:
        """A list of available options as strings."""
        return sorted([str(x) for x in self.resource.selects[self._identifier].selects])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.bridge.async_request_call(
            self.controller.set_state,
            device_id=self.resource.id,
            selects={
                self._identifier: option,
            },
        )


# Some lights (e.g. Home Decorators Collection pre-lit trees) expose brightness
# only as a ``brightness-presets`` category (low / medium / high) instead of a
# numeric ``brightness`` function. aioafero does not map it onto the Light
# model, so expose it here as a select backed by the raw device state.
BRIGHTNESS_PRESET_CLASS = "brightness-presets"
BRIGHTNESS_PRESET_ORDER = ("low", "medium", "high")


def get_raw_device(bridge: HubspaceBridge, device_id: str) -> AferoDevice | None:
    """Return the raw Afero device, or None when it is not tracked."""
    try:
        return bridge.api.get_afero_device(device_id)
    except DeviceNotFound:
        return None


def brightness_preset_sort_key(preset: str) -> int:
    """Sort known presets dimmest first, unknown ones last."""
    if preset in BRIGHTNESS_PRESET_ORDER:
        return BRIGHTNESS_PRESET_ORDER.index(preset)
    return len(BRIGHTNESS_PRESET_ORDER)


def get_brightness_presets(device: AferoDevice | None) -> list[str]:
    """Return the brightness presets a device supports, dimmest first."""
    if device is None:
        return []
    presets: list[str] = []
    for func in device.functions:
        if func.get("functionClass") == BRIGHTNESS_PRESET_CLASS:
            presets = [val["name"] for val in func.get("values", []) if val.get("name")]
    return sorted(presets, key=brightness_preset_sort_key)


class AferoBrightnessPresetSelect(HubspaceBaseEntity, SelectEntity):
    """Brightness preset (low / medium / high) for an Afero light."""

    _attr_icon = "mdi:brightness-6"

    def __init__(
        self,
        bridge: HubspaceBridge,
        controller: AferoController,
        resource: AferoModelResource,
        presets: list[str],
    ) -> None:
        """Initialize a brightness preset select."""
        super().__init__(bridge, controller, resource, instance=BRIGHTNESS_PRESET_CLASS)
        self._attr_name = "Brightness"
        self._presets = presets
        self._attr_options = [preset.capitalize() for preset in presets]

    @property
    def current_option(self) -> str | None:
        """The current brightness preset."""
        device = get_raw_device(self.bridge, self.resource.id)
        if device is None:
            return None
        for state in device.states:
            if (
                state.functionClass == BRIGHTNESS_PRESET_CLASS
                and state.value in self._presets
            ):
                return state.value.capitalize()
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the brightness preset."""
        preset = next(p for p in self._presets if p.capitalize() == option)
        await self.bridge.async_request_call(
            self.controller.update,
            self.resource.id,
            states=[
                {
                    "functionClass": BRIGHTNESS_PRESET_CLASS,
                    "functionInstance": None,
                    "value": preset,
                }
            ],
        )


def brightness_preset_entities(
    bridge: HubspaceBridge, resources
) -> list[AferoBrightnessPresetSelect]:
    """Create brightness preset selects for lights that support them."""
    entities = []
    for resource in resources:
        presets = get_brightness_presets(get_raw_device(bridge, resource.id))
        if presets:
            entities.append(
                AferoBrightnessPresetSelect(
                    bridge, bridge.api.lights, resource, presets
                )
            )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    bridge: HubspaceBridge = hass.data[DOMAIN][config_entry.entry_id]

    # add all current items in the controller
    entities = []
    for controller in bridge.api.controllers:
        if "selects" not in [x.name for x in fields(controller.ITEM_CLS)]:
            continue
        config_entry.async_on_unload(
            controller.subscribe(
                await generate_callback(bridge, controller, async_add_entities),
                event_filter=EventType.RESOURCE_ADDED,
            )
        )
        # Add any currently tracked entities
        entities.extend(
            [
                AferoSelectEntitiy(bridge, controller, resource, select)
                for resource in controller
                for select in resource.selects
            ]
        )

    # Brightness presets for lights (see AferoBrightnessPresetSelect)
    entities.extend(brightness_preset_entities(bridge, bridge.api.lights))

    async def add_brightness_presets(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add a brightness preset select for a newly added light."""
        async_add_entities(brightness_preset_entities(bridge, [resource]))

    config_entry.async_on_unload(
        bridge.api.lights.subscribe(
            add_brightness_presets, event_filter=EventType.RESOURCE_ADDED
        )
    )
    async_add_entities(entities)


async def generate_callback(bridge, controller, async_add_entities: callback):
    """Generate a callback function for handling new select entities.

    Args:
        bridge: HubspaceBridge instance for managing device communication
        controller: AferoController instance managing the device
        async_add_entities: Callback function to register new entities

    Returns:
        Callback function that adds new select entities when resources are added

    """

    async def add_entity_controller(
        event_type: EventType, resource: AferoModelResource
    ) -> None:
        """Add one or more Selects."""
        async_add_entities(
            [
                AferoSelectEntitiy(bridge, controller, resource, select)
                for select in resource.selects
            ]
        )

    return add_entity_controller
