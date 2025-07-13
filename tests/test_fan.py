"""Test the integration between Home Assistant Fans and Afero devices."""

from aioafero import AferoState
from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
)
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_instance = fan_zandra[0]
fan_zandra_entity_id = "fan.friendly_device_2_fan"


exhaust_fan = create_devices_from_data("fan-exhaust-fan.json")
exhaust_fan_instance = exhaust_fan[3]
exhaust_fan_instance_entity_id = "fan.r3_closet_fan"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked fan and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(fan_zandra)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "devices",
        "expected_entities",
    ),
    [
        (fan_zandra, [fan_zandra_entity_id]),
        (exhaust_fan, [exhaust_fan_instance_entity_id]),
    ],
)
async def test_async_setup_entry(devices, expected_entities, mocked_entry):
    """Ensure fans are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data(devices)
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
    bridge.fans[fan_zandra_instance.id].on.on = False
    await hass.services.async_call(
        "fan",
        "turn_on",
        {"entity_id": fan_zandra_entity_id, ATTR_PERCENTAGE: 50},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_PERCENTAGE] == 50
    assert entity.attributes[ATTR_PRESET_MODE] is None


@pytest.mark.asyncio
async def test_turn_on_preset(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    bridge.fans[fan_zandra_instance.id].on.on = False
    await hass.services.async_call(
        "fan",
        "turn_on",
        {
            "entity_id": fan_zandra_entity_id,
            ATTR_PERCENTAGE: 50,
            ATTR_PRESET_MODE: "breeze",
        },
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_PERCENTAGE] == 50
    assert entity.attributes[ATTR_PRESET_MODE] == "breeze"


@pytest.mark.asyncio
async def test_turn_on_limited(mocked_entry):
    """Ensure the service call turn_on works as expected."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(exhaust_fan)
    bridge.fans[exhaust_fan_instance.id].on.on = False
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "fan",
        "turn_on",
        {"entity_id": exhaust_fan_instance_entity_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == exhaust_fan_instance.id
    update = payload["values"][0]
    assert update["functionClass"] == "power"
    assert update["functionInstance"] == "fan-power"
    assert update["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    exhaust_fan_update = create_devices_from_data("fan-exhaust-fan.json")[3]
    modify_state(
        exhaust_fan_update,
        AferoState(
            functionClass="power",
            functionInstance="fan-power",
            value="on",
        ),
    )
    await bridge.generate_devices_from_data([exhaust_fan_update])
    await hass.async_block_till_done()
    assert bridge.fans[exhaust_fan_update.id].on.on
    test_entity = hass.states.get(exhaust_fan_instance_entity_id)
    assert test_entity is not None
    assert test_entity.state == "on"


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    """Ensure the service call turn_off works as expected."""
    hass, _, bridge = mocked_entity
    bridge.fans[fan_zandra_instance.id].on.on = True
    await hass.services.async_call(
        "fan",
        "turn_off",
        {"entity_id": fan_zandra_entity_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "off"


@pytest.mark.asyncio
async def test_set_percentage(mocked_entity):
    """Ensure the service call set_percentage works as expected."""
    hass, _, bridge = mocked_entity
    bridge.fans[fan_zandra_instance.id].on.on = False
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": fan_zandra_entity_id, "percentage": 100},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    assert payload["values"][1]["value"] == "fan-speed-6-100"
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_PERCENTAGE] == 100


@pytest.mark.asyncio
async def test_set_preset_mode(mocked_entity):
    """Ensure the service call set_preset_mode works as expected."""
    hass, _, bridge = mocked_entity
    bridge.fans[fan_zandra_instance.id].on.on = False
    bridge.fans[fan_zandra_instance.id].preset.enabled = False
    await hass.services.async_call(
        "fan",
        "set_preset_mode",
        {"entity_id": fan_zandra_entity_id, ATTR_PRESET_MODE: "breeze"},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    assert payload["values"][1]["functionInstance"] == "comfort-breeze"
    assert payload["values"][1]["value"] == "enabled"
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_PRESET_MODE] == "breeze"


@pytest.mark.asyncio
async def test_set_direction(mocked_entity):
    """Ensure the service call set_direction works as expected."""
    hass, _, bridge = mocked_entity
    bridge.fans[fan_zandra_instance.id].on.on = False
    bridge.fans[fan_zandra_instance.id].direction.forward = False
    await hass.services.async_call(
        "fan",
        "set_direction",
        {"entity_id": fan_zandra_entity_id, "direction": "forward"},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    assert payload["values"][1]["value"] == "forward"
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_DIRECTION] == "forward"
    # Reverse the fan
    await hass.services.async_call(
        "fan",
        "set_direction",
        {"entity_id": fan_zandra_entity_id, "direction": "reverse"},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id
    assert payload["values"][0]["value"] == "reverse"
    await hass.async_block_till_done()
    entity = hass.states.get(fan_zandra_entity_id)
    assert entity is not None
    assert entity.state == "on"
    assert entity.attributes[ATTR_DIRECTION] == "reverse"


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
    afero_data = hs_raw_from_dump("fan-ZandraFan.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    expected_entities = ["fan.friendly_device_2_fan"]
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None
