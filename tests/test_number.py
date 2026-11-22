"""Test the integration between Home Assistant Numbers and Afero devices."""

from aioafero import AferoState
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, modify_state

exhaust_fan_from_file = create_devices_from_data("fan-exhaust-fan.json")
exhaust_fan = exhaust_fan_from_file[2]
exhaust_fan_number_id = "number.r3_closet_auto_off_timer"

light_with_speed_from_file = create_devices_from_data("light-with-speed.json")
light_with_speed = light_with_speed_from_file[2]
light_with_speed_id = "number.landscaping_tree_lights_effect_speed"

rgbw_led_strip_from_file = create_devices_from_data("rgbw-led-strip.json")
rgbw_led_strip = rgbw_led_strip_from_file[0]
rgbw_led_strip_speed_id = "number.friendly_device_6_effect_speed"

ceiling_fan_from_file = create_devices_from_data("fan-ZandraFan.json")
ceiling_fan = ceiling_fan_from_file[0]
ceiling_fan_timer_id = "number.friendly_device_2_timer"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Exhaust Fan and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(exhaust_fan_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "dev",
        "expected_entities",
    ),
    [
        (exhaust_fan, [exhaust_fan_number_id]),
        (light_with_speed, [light_with_speed_id]),
        (rgbw_led_strip, [rgbw_led_strip_speed_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure numbers are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data([dev])
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity_id in expected_entities:
            ent = entity_reg.async_get(entity_id)
            assert ent is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_update(mocked_entry):
    """Ensure updates in aioafero set the correct states within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(exhaust_fan_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Now generate update event by emitting the json we've sent as incoming event
    hs_new_dev = create_devices_from_data("fan-exhaust-fan.json")[2]
    modify_state(
        hs_new_dev,
        AferoState(
            functionClass="auto-off-timer",
            functionInstance="auto-off",
            value=120,
        ),
    )
    await bridge.generate_devices_from_data([hs_new_dev])
    await hass.async_block_till_done()
    number = hass.states.get(exhaust_fan_number_id)
    assert number.state == "120"
    assert number.attributes["max"] == 1800
    assert number.attributes["min"] == 60
    assert number.attributes["step"] == 60
    assert number.attributes["unit_of_measurement"] == "seconds"


@pytest.mark.asyncio
async def test_light_speed_update(mocked_entry):
    """Ensure light effect speed updates propagate to Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(light_with_speed_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hs_new_dev = create_devices_from_data("light-with-speed.json")[2]
    modify_state(
        hs_new_dev,
        AferoState(
            functionClass="speed",
            functionInstance="color-sequence",
            value=5,
        ),
    )
    await bridge.generate_devices_from_data([hs_new_dev])
    await hass.async_block_till_done()
    number = hass.states.get(light_with_speed_id)
    assert number.state == "5"
    assert number.attributes["min"] == -10
    assert number.attributes["max"] == 10
    assert number.attributes["unit_of_measurement"] == "speed"


@pytest.mark.asyncio
async def test_light_speed_set_value(mocked_entry):
    """Ensure number.set_value updates light effect speed."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(light_with_speed_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": light_with_speed_id, "value": -3},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(light_with_speed_id)
    assert entity is not None
    assert entity.state == "-3.0"
    assert (
        bridge.lights[light_with_speed.id].numbers[("speed", "color-sequence")].value
        == -3
    )


@pytest.mark.asyncio
async def test_set_value(mocked_entity):
    """Ensure the service call set_value works as expected."""
    hass, _, bridge = mocked_entity
    bridge.exhaust_fans[exhaust_fan.id].numbers[
        ("auto-off-timer", "auto-off")
    ].value = 1200
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": exhaust_fan_number_id, "value": 120},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(exhaust_fan_number_id)
    assert entity is not None
    # Test fails because this fails to update. Checking the device shows its been updated
    # and its updated in HA, but not in the test
    assert entity.state == "120.0"


@pytest.mark.asyncio
async def test_add_new_device(mocked_entry):
    """Ensure newly added devices are properly discovered and registered with Home Assistant."""
    hass, entry, bridge = mocked_entry
    assert len(bridge.devices.items) == 0
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices.subscribers) > 0
    assert len(bridge.devices.subscribers["*"]) > 0
    # Now generate update event by emitting the json we've sent as incoming event
    hs_new_dev = create_devices_from_data("fan-exhaust-fan.json")[2]
    await bridge.generate_devices_from_data([hs_new_dev])
    await hass.async_block_till_done()
    expected_entities = [exhaust_fan_number_id]
    entity_reg = er.async_get(hass)
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
async def test_ceiling_fan_timer_update(mocked_entry):
    """Ensure the ceiling fan timer is discovered and cloud updates reach it."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(ceiling_fan_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # The timer is named after the ceiling-fan parent, so it needs the full dump
    assert er.async_get(hass).async_get(ceiling_fan_timer_id) is not None
    assert hass.states.get(ceiling_fan_timer_id).state == "0"
    # A discovery poll lists every device, including the ceiling-fan parent
    hs_new_devs = create_devices_from_data("fan-ZandraFan.json")
    modify_state(
        hs_new_devs[0],
        AferoState(functionClass="timer", functionInstance="fan-power", value=90),
    )
    await bridge.generate_devices_from_data(hs_new_devs)
    await hass.async_block_till_done()
    number = hass.states.get(ceiling_fan_timer_id)
    assert number.state == "90"
    assert number.attributes["min"] == 0
    assert number.attributes["max"] == 1440
    assert number.attributes["step"] == 1
    assert number.attributes["unit_of_measurement"] == "minutes"


@pytest.mark.asyncio
async def test_ceiling_fan_timer_set_value(mocked_entry):
    """Ensure set_value sends whole minutes as an int, which the cloud requires."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(ceiling_fan_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": ceiling_fan_timer_id, "value": 30},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    value = bridge.fans[ceiling_fan.id].numbers[("timer", "fan-power")].value
    assert value == 30
    assert isinstance(value, int)
    assert hass.states.get(ceiling_fan_timer_id).state == "30"
