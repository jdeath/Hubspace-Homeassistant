"""Test the integration between Home Assistant Lights and Afero devices."""

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
)
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.hubspace import light

from .utils import create_devices_from_data, hs_raw_from_dump

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]

switch_dimmer = create_devices_from_data("dimmer-HPDA1110NWBP.json")
switch_dimmer_light = switch_dimmer[0]
switch_dimmer_light_id = "light.laundry_room_light"

rgb_temp_light = create_devices_from_data("light-rgb_temp.json")[0]
light_a21 = create_devices_from_data("light-a21.json")[0]
light_a21_id = "light.friendly_device_53_light"
rgbw_led_strip = create_devices_from_data("rgbw-led-strip.json")[0]

trim_light_parent = create_devices_from_data("light-with-trim.json")[0]
trim_light_trim_id = f"{trim_light_parent.id}-light-trim"
trim_light_entity_id = "light.dining_room_light_1_trim"
trim_light_main_entity_id = "light.dining_room_light_1_main"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Light and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([light_a21])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_dimmer(mocked_entry):
    """Initialize a mocked dimmer switch and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([switch_dimmer_light])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.parametrize(
    (
        "color_mode",
        "supported",
        "expected",
    ),
    [
        # No current mode and none supported
        (None, {}, ColorMode.ONOFF),
        # No current mode and a mode is supported
        (None, {ColorMode.COLOR_TEMP}, ColorMode.COLOR_TEMP),
        # RGB mode
        ("color", {}, ColorMode.RGB),
        # White - Temp
        (
            "white",
            {ColorMode.COLOR_TEMP, ColorMode.ONOFF},
            ColorMode.COLOR_TEMP,
        ),
        # White - Brightness
        (
            "white",
            {ColorMode.BRIGHTNESS, ColorMode.ONOFF},
            ColorMode.BRIGHTNESS,
        ),
        # White - trim-style (RGB advertised; HA 2026 has no filterable WHITE)
        (
            "white",
            {ColorMode.RGB, ColorMode.ONOFF},
            ColorMode.RGB,
        ),
        # White - fallback
        ("white", set(), ColorMode.ONOFF),
        # Just fallback
        (None, set(), ColorMode.ONOFF),
    ],
)
def test_get_color_mode(color_mode, supported, expected, mocked_entity):
    """Ensure the correct color mode is selected."""
    tmp_light = mocked_entity[2].lights[light_a21.id]
    if color_mode:
        tmp_light.color_mode.mode = color_mode
    else:
        tmp_light.color_mode = None
    assert light.get_color_mode(tmp_light, supported) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "dev",
        "expected_entities",
    ),
    [
        (light_a21, [light_a21_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure lights are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data([dev])
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_turn_on(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    bridge.lights[light_a21.id].on.on = False
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": light_a21_id, ATTR_BRIGHTNESS: 64},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(light_a21_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes["brightness"] == 64
    assert bridge.lights[light_a21.id].brightness == 25


@pytest.mark.asyncio
async def test_turn_on_temp(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    bridge.lights[light_a21.id].on.on = False
    bridge.lights[light_a21.id].color_mode.mode = "no"
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": light_a21_id, ATTR_COLOR_TEMP_KELVIN: 3000},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(light_a21_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_EFFECT] is None
    assert entity.attributes[ATTR_COLOR_TEMP_KELVIN] == 3000
    assert entity.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP


@pytest.mark.asyncio
async def test_turn_on_color(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    bridge.lights[light_a21.id].on.on = False
    bridge.lights[light_a21.id].color_mode.mode = "no"
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": light_a21_id, ATTR_RGB_COLOR: (50, 100, 150)},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(light_a21_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_EFFECT] is None
    assert entity.attributes[ATTR_COLOR_TEMP_KELVIN] is None
    assert entity.attributes[ATTR_COLOR_MODE] == ColorMode.RGB
    assert entity.attributes[ATTR_RGB_COLOR] == (50, 100, 150)


@pytest.mark.asyncio
async def test_turn_on_effect(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    bridge.lights[light_a21.id].on.on = False
    bridge.lights[light_a21.id].color_mode.mode = "no"
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": light_a21_id, ATTR_EFFECT: "rainbow"},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert bridge.lights[light_a21.id].effect.effect == "rainbow"
    assert bridge.lights[light_a21.id].color_mode.mode == "sequence"
    entity = hass.states.get(light_a21_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_EFFECT] == "rainbow"


@pytest.mark.asyncio
async def test_turn_on_dimmer(mocked_dimmer):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_dimmer
    bridge.lights[switch_dimmer_light.id].on.on = False
    assert not bridge.lights[switch_dimmer_light.id].is_on
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": switch_dimmer_light_id},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(switch_dimmer_light_id)
    assert entity is not None
    assert entity.state == "on"


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    """Ensure the service call turn_off works as expected."""
    hass, _, bridge = mocked_entity
    bridge.lights[light_a21.id].on.on = True
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": light_a21_id},
        blocking=True,
    )
    await bridge.async_block_until_done()
    entity = hass.states.get(light_a21_id)
    assert entity is not None
    assert entity.state == "off"


@pytest.mark.asyncio
async def test_turn_off_dimmer(mocked_dimmer):
    """Ensure the service call turn_off works as expected."""
    hass, _, bridge = mocked_dimmer
    bridge.lights[switch_dimmer_light.id].on.on = True
    assert bridge.lights[switch_dimmer_light.id].is_on
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": switch_dimmer_light_id},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(switch_dimmer_light_id)
    assert entity is not None
    assert entity.state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "file",
        "expected_device_count",
        "expected_entities",
    ),
    [
        ("dimmer-HPDA1110NWBP.json", 1, [switch_dimmer_light_id]),
        (
            "light-flushmount.json",
            1,
            [
                "light.ceiling_light_color",
                "light.ceiling_light_white",
            ],
        ),
        (
            "light-with-trim.json",
            1,
            [
                trim_light_main_entity_id,
                trim_light_entity_id,
            ],
        ),
    ],
)
async def test_add_new_device(
    file, expected_device_count, expected_entities, mocked_entry
):
    """Ensure newly added devices are properly discovered and registered with Home Assistant."""
    hass, entry, bridge = mocked_entry
    assert len(bridge.devices.items) == 0
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices.subscribers) > 0
    assert len(bridge.devices.subscribers["*"]) > 0
    # Now generate update event by emitting the json we've sent as incoming event
    afero_data = hs_raw_from_dump(file)
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == expected_device_count
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None, (
            f"Unable to find entity {entity}"
        )


@pytest.fixture
async def mocked_trim_light(mocked_entry):
    """Initialize split trim/main lights from the accent-ring dump."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(
        create_devices_from_data("light-with-trim.json")
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for hub_light in bridge.lights.items:
        hub_light.available = True
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_trim_entity_supports_rgb_not_color_temp(mocked_trim_light):
    """Trim zone has RGB in HA but not COLOR_TEMP (API white-only warm)."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    assert trim.color_temperature is None
    assert trim.supports_color_white
    entity = hass.states.get(trim_light_entity_id)
    assert entity is not None
    assert ColorMode.RGB in entity.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP not in entity.attributes["supported_color_modes"]


def _get_hubspace_light(hass, entity_id: str):
    """Return the Hubspace LightEntity for a registered entity_id."""
    entities = hass.data["light"].entities
    if isinstance(entities, dict):
        return entities[entity_id]
    for entity in entities:
        if entity.entity_id == entity_id:
            return entity
    raise AssertionError(f"No light entity registered for {entity_id}")


@pytest.mark.asyncio
async def test_trim_api_white_reports_ha_rgb_mode(mocked_trim_light):
    """Inbound API color-mode white must not map to ONOFF (avoids rgb mismatch)."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "white"
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    light_ent.on_update()
    light_ent.async_write_ha_state()
    await hass.async_block_till_done()
    assert light_ent.color_mode == ColorMode.RGB
    assert light_ent.rgb_color == (255, 255, 255)


@pytest.mark.asyncio
async def test_trim_turn_on_white_sends_color_mode(mocked_trim_light, mocker):
    """Turn-on while API is white must PUT color-mode white without color-temperature."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.on.on = False
    trim.color_mode.mode = "white"
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    await light_ent.async_turn_on(brightness=128)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    sent.assert_called()
    white_calls = [
        c for c in sent.call_args_list if c.kwargs.get("color_mode") == "white"
    ]
    assert white_calls, "expected at least one set_state with color_mode=white"
    call_kwargs = white_calls[-1].kwargs
    assert call_kwargs["color_mode"] == "white"
    assert call_kwargs.get("temperature") is None
    assert call_kwargs["on"] is True
    assert call_kwargs["brightness"] == 50
