"""Test the integration between Home Assistant Switches and Afero devices."""

from aioafero import AferoState
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

transformer_from_file = create_devices_from_data("transformer.json")
transformer = transformer_from_file[0]
transformer_entity_zone_1 = "switch.friendly_device_6_zone_1"
transformer_entity_zone_2 = "switch.friendly_device_6_zone_2"
transformer_entity_zone_3 = "switch.friendly_device_6_zone_3"

hs_switch_from_file = create_devices_from_data("switch-HPSA11CWB.json")
hs_switch = create_devices_from_data("switch-HPSA11CWB.json")[0]
hs_switch_id = "switch.basement_furnace_switch"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Switch and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(hs_switch_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_entity_toggled(mocked_entry):
    """Initialize a mocked instanced Switch and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(transformer_from_file)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_exhaust_fan(mocked_entry):
    """Initialize a mocked exhaust fan and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    # Now generate update event by emitting the json we've sent as incoming event
    await bridge.generate_devices_from_data(
        create_devices_from_data("fan-exhaust-fan.json")
    )
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_light_speaker(mocked_entry):
    """Initialize a mocked light with a speaker and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    # Now generate update event by emitting the json we've sent as incoming event
    await bridge.generate_devices_from_data(
        create_devices_from_data("light-with-speaker.json")
    )
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "dev",
        "expected_entities",
    ),
    [
        (hs_switch, [hs_switch_id]),
        (
            transformer,
            [
                transformer_entity_zone_1,
                "switch.friendly_device_6_zone_1",
                "switch.friendly_device_6_zone_1",
            ],
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure switches are properly discovered and registered with Home Assistant."""
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
async def test_turn_on_toggle(mocked_entity_toggled):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity_toggled
    assert not bridge.switches[transformer.id].on["zone-3"].on
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": transformer_entity_zone_3},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == transformer.id
    update = payload["values"][0]
    assert update["functionClass"] == "toggle"
    assert update["functionInstance"] == "zone-3"
    assert update["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    transformer_update = create_devices_from_data("transformer.json")
    modify_state(
        transformer_update[0],
        AferoState(
            functionClass="toggle",
            functionInstance="zone-3",
            value="on",
        ),
    )
    await bridge.generate_devices_from_data(transformer_update)
    await hass.async_block_till_done()
    entity = hass.states.get(transformer_entity_zone_3)
    assert entity is not None
    assert entity.state == "on"


@pytest.mark.asyncio
async def test_turn_on(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    assert not bridge.switches[hs_switch.id].on[None].on
    assert hass.states.get(hs_switch_id).state == "off"
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": hs_switch_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == hs_switch.id
    update = payload["values"][0]
    assert update["functionClass"] == "power"
    assert update["functionInstance"] is None
    assert update["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    hs_switch_update = create_devices_from_data("switch-HPSA11CWB.json")
    modify_state(
        hs_switch_update[0],
        AferoState(
            functionClass="power",
            functionInstance=None,
            value="on",
        ),
    )
    await bridge.generate_devices_from_data(hs_switch_update)
    await hass.async_block_till_done()
    entity = hass.states.get(hs_switch_id)
    assert entity is not None
    assert entity.state == "on"


@pytest.mark.asyncio
async def test_turn_off_toggle(mocked_entity_toggled):
    """Ensure the service call turn_off works as expected."""
    hass, _, bridge = mocked_entity_toggled
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": transformer_entity_zone_2},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == transformer.id
    # Now generate update event by emitting the json we've sent as incoming event
    transformer_update = create_devices_from_data("transformer.json")[0]
    modify_state(
        transformer_update,
        AferoState(
            functionClass="toggle",
            functionInstance="zone-2",
            value="off",
        ),
    )
    await bridge.generate_devices_from_data([transformer_update])
    await hass.async_block_till_done()
    entity = hass.states.get(transformer_entity_zone_2)
    assert entity is not None
    assert entity.state == "off"


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    """Ensure the service call turn_off works as expected."""
    hass, _, bridge = mocked_entity
    bridge.switches[hs_switch.id].on[None].on = True
    assert bridge.switches[hs_switch.id].on[None].on
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": hs_switch_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == hs_switch.id
    update = payload["values"][0]
    assert update["functionClass"] == "power"
    assert update["functionInstance"] is None
    assert update["value"] == "off"
    # Now generate update event by emitting the json we've sent as incoming event
    hs_switch_update = create_devices_from_data("switch-HPSA11CWB.json")[0]
    modify_state(
        hs_switch_update,
        AferoState(
            functionClass="toggle",
            functionInstance=None,
            value="off",
        ),
    )
    await bridge.generate_devices_from_data([hs_switch_update])
    await hass.async_block_till_done()
    test_switch = hass.states.get(hs_switch_id)
    assert test_switch is not None
    assert test_switch.state == "off"


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
    afero_data = hs_raw_from_dump("transformer.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    for entity in [
        transformer_entity_zone_1,
        transformer_entity_zone_2,
        transformer_entity_zone_3,
    ]:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
async def test_exhaust_fan_names(mocked_exhaust_fan):
    """Ensure there was no API break when between aioafero 4 and 5 for the plugin."""
    hass, _, bridge = mocked_exhaust_fan
    assert len(bridge.switches.items) == 5
    expected_switches = [
        "switch.r3_closet_humidity_sensor_led",
        "switch.r3_closet_motion_sensor_led",
        "switch.r3_closet_humidity_detection_enabled",
        "switch.r3_closet_speaker_power",
        "switch.r3_closet_motion_detection_enabled_exhaust_fan",
    ]
    entity_reg = er.async_get(hass)
    for entity in expected_switches:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
async def test_light_speaker_power(mocked_light_speaker):
    """Ensure that the light speaker creates a switch."""
    hass, _, bridge = mocked_light_speaker
    assert len(bridge.switches.items) == 1
    entity_reg = er.async_get(hass)
    speaker_light_id = "switch.office_bathroom_light_speaker_power"
    assert entity_reg.async_get(speaker_light_id) is not None
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": speaker_light_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == "3bec6eaa-3d87-4f3c-a065-a2b32f87c39f"
    update = payload["values"][0]
    assert update["functionClass"] == "toggle"
    assert update["functionInstance"] == "speaker-power"
    assert update["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    hs_switch_update = create_devices_from_data("light-with-speaker.json")
    modify_state(
        hs_switch_update[0],
        AferoState(
            functionClass="toggle",
            functionInstance="speaker-power",
            value="on",
        ),
    )
    await bridge.generate_devices_from_data(hs_switch_update)
    await hass.async_block_till_done()
    test_switch = hass.states.get(speaker_light_id)
    assert test_switch is not None
    assert test_switch.state == "on"
