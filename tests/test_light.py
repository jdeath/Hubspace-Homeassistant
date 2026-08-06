"""Test the integration between Home Assistant Lights and Afero devices."""

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_WHITE,
    ColorMode,
)
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.hubspace import light

from .utils import create_devices_from_data, hs_raw_from_dump

switch_dimmer = create_devices_from_data("dimmer-HPDA1110NWBP.json")
switch_dimmer_light = switch_dimmer[0]
switch_dimmer_light_id = "light.laundry_room"

light_a21 = create_devices_from_data("light-a21.json")[0]
light_a21_id = "light.friendly_device_53"

trim_light_parent = create_devices_from_data("light-with-trim.json")[0]
trim_light_trim_id = f"{trim_light_parent.id}-light-trim"
trim_light_main_id = f"{trim_light_parent.id}-light-main"
trim_light_entity_id = "light.dining_room_light_1_trim"
trim_light_main_entity_id = "light.dining_room_light_1_main"

flushmount_from_file = create_devices_from_data("light-flushmount.json")
flushmount_dev = flushmount_from_file[0]
flushmount_color_entity_id = "light.ceiling_light_color"
flushmount_white_entity_id = "light.ceiling_light_white"

rgbcw_strip = create_devices_from_data("rgbcw-led-strip.json")[0]
rgbcw_color_entity_id = "light.kitchen_counter_light_2_color"
rgbcw_white_entity_id = "light.kitchen_counter_light_2_white"


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
        # White - trim-style (API white maps to HA white when advertised)
        (
            "white",
            {ColorMode.RGB, ColorMode.WHITE, ColorMode.ONOFF},
            ColorMode.WHITE,
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
                flushmount_color_entity_id,
                flushmount_white_entity_id,
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
        (
            "rgbcw-led-strip.json",
            1,
            [
                rgbcw_color_entity_id,
                rgbcw_white_entity_id,
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
async def mocked_flushmount_light(mocked_entry):
    """Initialize a dual-channel flushmount light."""
    hass, entry, bridge = mocked_entry
    # Wire presentation policy before discovery so Auto splits this model.
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await bridge.generate_devices_from_data(
        create_devices_from_data("light-flushmount.json")
    )
    await hass.async_block_till_done()
    for hub_light in bridge.lights.items:
        hub_light.available = True
    yield hass, entry, bridge
    await bridge.close()


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
async def test_trim_entity_supports_rgb_and_white_not_color_temp(mocked_trim_light):
    """Trim zone advertises RGB and white (API white), not COLOR_TEMP."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    assert trim.color_temperature is None
    assert trim.supports_color_white
    entity = hass.states.get(trim_light_entity_id)
    assert entity is not None
    assert ColorMode.RGB in entity.attributes["supported_color_modes"]
    assert ColorMode.WHITE in entity.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP not in entity.attributes["supported_color_modes"]


@pytest.mark.asyncio
async def test_main_entity_supports_color_temp_not_ha_white(mocked_trim_light):
    """Main zone uses COLOR_TEMP for kelvin; must not advertise HA white mode."""
    hass, _, bridge = mocked_trim_light
    main = bridge.lights[trim_light_main_id]
    assert main.supports_color_temperature
    assert main.supports_color_white
    entity = hass.states.get(trim_light_main_entity_id)
    assert entity is not None
    assert ColorMode.COLOR_TEMP in entity.attributes["supported_color_modes"]
    assert ColorMode.RGB in entity.attributes["supported_color_modes"]
    assert ColorMode.WHITE not in entity.attributes["supported_color_modes"]


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
async def test_trim_api_white_reports_ha_white_mode(mocked_trim_light):
    """Inbound API color-mode white maps to HA white with no rgb_color."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "white"
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    light_ent.on_update()
    light_ent.async_write_ha_state()
    await hass.async_block_till_done()
    assert light_ent.color_mode == ColorMode.WHITE
    assert light_ent.rgb_color is None


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


@pytest.mark.asyncio
async def test_trim_turn_on_white_attr_switches_from_rgb(mocked_trim_light, mocker):
    """HA white selection must PUT color-mode white when trim was in API color."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "color"
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    await light_ent.async_turn_on(white=True)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["color_mode"] == "white"
    assert call_kwargs.get("temperature") is None
    assert call_kwargs.get("color") is None


@pytest.mark.asyncio
async def test_trim_ha_white_button_from_rgb_when_white_is_none(
    mocked_trim_light, mocker
):
    """HA core may pass white=None after converting white=True without brightness."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "color"
    trim.on.on = True
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    mocker.patch.object(
        type(light_ent),
        "brightness",
        new_callable=mocker.PropertyMock,
        return_value=None,
    )
    await light_ent.async_turn_on(**{ATTR_WHITE: None})
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["color_mode"] == "white"
    assert call_kwargs.get("color") is None


@pytest.mark.asyncio
async def test_trim_turn_on_brightness_in_rgb_mode_omits_color_mode(
    mocked_trim_light, mocker
):
    """Brightness-only while in API color must not force color-mode white."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "color"
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    await light_ent.async_turn_on(brightness=128)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs.get("color_mode") is None


@pytest.mark.asyncio
async def test_trim_turn_on_white_int_scales_brightness(mocked_trim_light, mocker):
    """HA W button sends white 0-255; API expects brightness 1-100."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "color"
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    await light_ent.async_turn_on(**{ATTR_WHITE: 128})
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["color_mode"] == "white"
    assert call_kwargs["brightness"] == 50


@pytest.mark.asyncio
async def test_trim_turn_on_white_true_defaults_brightness_when_unknown(
    mocked_trim_light, mocker
):
    """White mode without HA brightness falls back to 100% when pct is unset."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.color_mode.mode = "color"
    trim.dimming.brightness = None
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    await light_ent.async_turn_on(white=True)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["color_mode"] == "white"
    assert call_kwargs["brightness"] == 100


@pytest.mark.asyncio
async def test_main_turn_on_white_does_not_send_api_white(mocked_trim_light, mocker):
    """Main has CCT; HA white must not route to API color-mode white."""
    hass, _, bridge = mocked_trim_light
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, trim_light_main_entity_id)
    await light_ent.async_turn_on(white=True)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs.get("color_mode") is None


@pytest.mark.asyncio
async def test_brightness_none_when_no_dimming(mocked_dimmer):
    """Lights without dimming must not report HA brightness."""
    hass, _, bridge = mocked_dimmer
    light_ent = _get_hubspace_light(hass, switch_dimmer_light_id)
    light_ent.resource.dimming = None
    assert light_ent.brightness is None


@pytest.mark.asyncio
async def test_brightness_defaults_when_pct_none(mocked_trim_light):
    """Missing API brightness pct defaults to full scale for HA."""
    hass, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.dimming.brightness = None
    light_ent = _get_hubspace_light(hass, trim_light_entity_id)
    assert light_ent.brightness == 255


@pytest.mark.asyncio
async def test_rgb_color_none_without_color_feature(mocked_dimmer):
    """Non-RGB lights must not expose rgb_color."""
    hass, _, bridge = mocked_dimmer
    light_ent = _get_hubspace_light(hass, switch_dimmer_light_id)
    assert light_ent.resource.color is None
    assert light_ent.rgb_color is None


@pytest.mark.asyncio
async def test_is_api_white_zone_trim_vs_main(mocked_trim_light):
    """Trim is white-only; main uses CCT for kelvin."""
    _, _, bridge = mocked_trim_light
    assert light.is_api_white_zone(bridge.lights[trim_light_trim_id])
    assert not light.is_api_white_zone(bridge.lights[trim_light_main_id])


@pytest.mark.asyncio
async def test_default_brightness_pct_fallback(mocked_trim_light):
    """Cover 100% fallback when dimming exists but pct is unknown."""
    _, _, bridge = mocked_trim_light
    trim = bridge.lights[trim_light_trim_id]
    trim.dimming.brightness = None
    assert light.default_brightness_pct(trim) == 100


@pytest.mark.asyncio
async def test_flushmount_color_supports_rgb_not_cct(mocked_flushmount_light):
    """Flushmount color light exposes RGB; white light owns CCT."""
    hass, _, bridge = mocked_flushmount_light
    resource = bridge.lights[flushmount_dev.id]
    assert resource.is_dual_channel
    assert resource.supports_color
    assert resource.supports_color_temperature
    color_ent = hass.states.get(flushmount_color_entity_id)
    white_ent = hass.states.get(flushmount_white_entity_id)
    assert ColorMode.RGB in color_ent.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP not in color_ent.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP in white_ent.attributes["supported_color_modes"]
    assert ColorMode.RGB not in white_ent.attributes["supported_color_modes"]


@pytest.mark.asyncio
async def test_flushmount_turn_on_rgb_sends_color_mode(mocked_flushmount_light, mocker):
    """RGB turn-on targets the shared light with color channel context."""
    hass, _, bridge = mocked_flushmount_light
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, flushmount_color_entity_id)
    await light_ent.async_turn_on(rgb_color=(10, 20, 30), brightness=128)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["device_id"] == flushmount_dev.id
    assert call_kwargs["color_mode"] == "color"
    assert call_kwargs["channel"] == "color"
    assert call_kwargs["color"] == (10, 20, 30)
    assert call_kwargs["brightness"] == 50


@pytest.fixture
async def mocked_rgbcw_strip_light(mocked_entry):
    """Initialize a combined dual-channel RGBCW strip light."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([rgbcw_strip])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_should_split_dual_channel_light_flushmount(mocked_flushmount_light):
    """Dual-channel flushmounts present as color + white light entities."""
    _, _, bridge = mocked_flushmount_light
    resource = bridge.lights[flushmount_dev.id]
    assert light.should_split_dual_channel_light(resource) is True
    entities = light.entities_for_light(bridge, bridge.lights, resource)
    assert [entity.unique_id for entity in entities] == [
        f"{resource.id}.color",
        f"{resource.id}.white",
    ]


@pytest.mark.asyncio
async def test_should_split_dual_channel_light_strip(mocked_rgbcw_strip_light):
    """Dual-channel RGBCW strips also present as color + white light entities."""
    _, _, bridge = mocked_rgbcw_strip_light
    resource = bridge.lights[rgbcw_strip.id]
    assert light.should_split_dual_channel_light(resource) is True
    entities = light.entities_for_light(bridge, bridge.lights, resource)
    assert [entity.unique_id for entity in entities] == [
        f"{resource.id}.color",
        f"{resource.id}.white",
    ]


@pytest.mark.asyncio
async def test_rgbcw_strip_split_light_entities(mocked_rgbcw_strip_light):
    """RGBCW strip discovers as color + white lights, not channel switches."""
    hass, _, bridge = mocked_rgbcw_strip_light
    resource = bridge.lights[rgbcw_strip.id]
    assert resource.is_dual_channel
    entity_reg = er.async_get(hass)
    assert entity_reg.async_get(rgbcw_color_entity_id) is not None
    assert entity_reg.async_get(rgbcw_white_entity_id) is not None
    assert entity_reg.async_get("light.kitchen_counter_light_2") is None
    assert entity_reg.async_get("switch.kitchen_counter_light_2_color") is None
    assert entity_reg.async_get("switch.kitchen_counter_light_2_white") is None
    color_ent = hass.states.get(rgbcw_color_entity_id)
    white_ent = hass.states.get(rgbcw_white_entity_id)
    assert ColorMode.RGB in color_ent.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP not in color_ent.attributes["supported_color_modes"]
    assert ColorMode.COLOR_TEMP in white_ent.attributes["supported_color_modes"]
    assert ColorMode.RGB not in white_ent.attributes["supported_color_modes"]


@pytest.mark.asyncio
async def test_rgbcw_color_turn_on_uses_channel(mocked_rgbcw_strip_light, mocker):
    """RGBCW color light turn-on targets set_state with channel=color."""
    hass, _, bridge = mocked_rgbcw_strip_light
    sent = mocker.spy(bridge.lights, "set_state")
    light_ent = _get_hubspace_light(hass, rgbcw_color_entity_id)
    await light_ent.async_turn_on(rgb_color=(12, 34, 56), brightness=128)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    call_kwargs = sent.call_args.kwargs
    assert call_kwargs["device_id"] == rgbcw_strip.id
    assert call_kwargs["channel"] == "color"
    assert call_kwargs["color_mode"] == "color"
    assert call_kwargs["color"] == (12, 34, 56)


@pytest.mark.asyncio
async def test_displayed_brightness_pct_channel_entities(mocked_rgbcw_strip_light):
    """Split channel entities read brightness from their own channel."""
    _, _, bridge = mocked_rgbcw_strip_light
    resource = bridge.lights[rgbcw_strip.id]
    resource.channels["color"].brightness = 80
    resource.channels["white"].brightness = 40
    resource.dimming.brightness = 55
    assert light.displayed_brightness_pct(resource, channel="color") == 80
    assert light.displayed_brightness_pct(resource, channel="white") == 40


penrose_light = create_devices_from_data("light-penrose.json")[0]
penrose_main_entity_id = "light.vanity_bar_light"
penrose_night_entity_id = "light.vanity_bar_light_night_light"


@pytest.fixture
async def mocked_penrose(mocked_entry):
    """Initialize a Penrose vanity light with night-light color-mode."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([penrose_light])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_penrose_discovers_night_light_entity(mocked_penrose):
    """Fixtures with night-light color-mode get a second on/off light entity."""
    hass, _, bridge = mocked_penrose
    assert light.has_night_light_mode(bridge.lights[penrose_light.id])
    assert hass.states.get(penrose_main_entity_id) is not None
    night = hass.states.get(penrose_night_entity_id)
    assert night is not None
    assert night.attributes["supported_color_modes"] == [ColorMode.ONOFF]


@pytest.mark.asyncio
async def test_night_light_turn_on_stashes_previous_mode(mocked_penrose, mocker):
    """Enabling night-light stores the prior mode and asks aioafero to set it."""
    hass, entry, bridge = mocked_penrose
    hub = hass.data["hubspace"][entry.entry_id]
    resource = bridge.lights[penrose_light.id]
    resource.on.on = False
    resource.color_mode.mode = "white"
    sent = mocker.spy(bridge.lights, "set_state")
    night_ent = _get_hubspace_light(hass, penrose_night_entity_id)
    await night_ent.async_turn_on()
    await bridge.async_block_until_done()
    assert hub.night_light_previous_modes[penrose_light.id] == "white"
    assert hub.night_light_was_on[penrose_light.id] is False
    assert sent.call_args.kwargs["color_mode"] == "night-light"
    assert sent.call_args.kwargs["on"] is True


@pytest.mark.asyncio
async def test_night_light_turn_off_restores_mode_when_was_on(mocked_penrose, mocker):
    """Disabling night-light while previously on restores the prior mode."""
    hass, entry, bridge = mocked_penrose
    hub = hass.data["hubspace"][entry.entry_id]
    resource = bridge.lights[penrose_light.id]
    resource.on.on = True
    resource.color_mode.mode = "color"
    sent = mocker.spy(bridge.lights, "set_state")
    night_ent = _get_hubspace_light(hass, penrose_night_entity_id)
    await night_ent.async_turn_on()
    await night_ent.async_turn_off()
    await bridge.async_block_until_done()
    assert hub.night_light_was_on[penrose_light.id] is True
    assert sent.call_args.kwargs["color_mode"] == "color"
    assert sent.call_args.kwargs["on"] is True


@pytest.mark.asyncio
async def test_night_light_turn_off_powers_off_when_was_off(mocked_penrose, mocker):
    """Disabling night-light when it was enabled from off only powers off."""
    hass, _, bridge = mocked_penrose
    resource = bridge.lights[penrose_light.id]
    resource.on.on = False
    resource.color_mode.mode = "white"
    sent = mocker.spy(bridge.lights, "set_state")
    night_ent = _get_hubspace_light(hass, penrose_night_entity_id)
    await night_ent.async_turn_on()
    resource.on.on = True
    resource.color_mode.mode = "night-light"
    await night_ent.async_turn_off()
    await bridge.async_block_until_done()
    assert sent.call_args.kwargs["on"] is False
    assert sent.call_args.kwargs.get("color_mode") is None


@pytest.mark.asyncio
async def test_night_light_turn_off_after_reload_stays_on(mocked_penrose, mocker):
    """Missing was_on after reload defaults to restoring mode while staying on."""
    hass, entry, bridge = mocked_penrose
    hub = hass.data["hubspace"][entry.entry_id]
    resource = bridge.lights[penrose_light.id]
    resource.on.on = True
    resource.color_mode.mode = "night-light"
    hub.night_light_previous_modes[penrose_light.id] = "white"
    hub.night_light_was_on.clear()
    sent = mocker.spy(bridge.lights, "set_state")
    night_ent = _get_hubspace_light(hass, penrose_night_entity_id)
    await night_ent.async_turn_off()
    await bridge.async_block_until_done()
    assert sent.call_args.kwargs["on"] is True
    assert sent.call_args.kwargs["color_mode"] == "white"


@pytest.mark.asyncio
async def test_main_reports_off_while_night_light_active(mocked_penrose):
    """Main light reports off while night-light mode owns the fixture."""
    hass, _, bridge = mocked_penrose
    resource = bridge.lights[penrose_light.id]
    resource.on.on = True
    resource.color_mode.mode = "night-light"
    main_ent = _get_hubspace_light(hass, penrose_main_entity_id)
    night_ent = _get_hubspace_light(hass, penrose_night_entity_id)
    assert main_ent.is_on is False
    assert night_ent.is_on is True


@pytest.mark.asyncio
async def test_main_turn_on_restores_mode_when_stuck_in_night_light(
    mocked_penrose, mocker
):
    """Main turn-on while stored mode is night-light restores the prior mode first."""
    hass, entry, bridge = mocked_penrose
    hub = hass.data["hubspace"][entry.entry_id]
    resource = bridge.lights[penrose_light.id]
    resource.on.on = False
    resource.color_mode.mode = "night-light"
    hub.night_light_previous_modes[penrose_light.id] = "color"
    sent = mocker.spy(bridge.lights, "set_state")
    main_ent = _get_hubspace_light(hass, penrose_main_entity_id)
    await main_ent.async_turn_on()
    await bridge.async_block_until_done()
    assert sent.call_count == 2
    assert sent.call_args_list[0].kwargs == {
        "device_id": penrose_light.id,
        "color_mode": "color",
    }
    assert sent.call_args_list[1].kwargs["on"] is True
    assert sent.call_args_list[1].kwargs["color_mode"] == "color"


@pytest.mark.asyncio
async def test_main_turn_on_rgb_while_off_in_night_light_sets_mode_first(
    mocked_penrose, mocker
):
    """Explicit RGB while off in night-light still mode-before-powers."""
    hass, _, bridge = mocked_penrose
    resource = bridge.lights[penrose_light.id]
    resource.on.on = False
    resource.color_mode.mode = "night-light"
    sent = mocker.spy(bridge.lights, "set_state")
    main_ent = _get_hubspace_light(hass, penrose_main_entity_id)
    await main_ent.async_turn_on(rgb_color=(10, 20, 30))
    await bridge.async_block_until_done()
    assert sent.call_count == 2
    assert sent.call_args_list[0].kwargs == {
        "device_id": penrose_light.id,
        "color_mode": "color",
    }
    assert sent.call_args_list[1].kwargs["color_mode"] == "color"
    assert sent.call_args_list[1].kwargs["color"] == (10, 20, 30)
    assert sent.call_args_list[1].kwargs["on"] is True
