import pytest
from aiohubspace.v1.device import HubspaceState
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data, modify_state

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]

switch_dimmer = create_devices_from_data("dimmer-HPDA1110NWBP.json")
switch_dimmer_light = switch_dimmer[0]
switch_dimmer_light_id = "light.laundry_room_light"

rgb_temp_light = create_devices_from_data("light-rgb_temp.json")[0]
light_a21 = create_devices_from_data("light-a21.json")[0]
light_a21_id = "light.friendly_device_53_light"
rgbw_led_strip = create_devices_from_data("rgbw-led-strip.json")[0]


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.lights.initialize_elem(light_a21)
    await bridge.devices.initialize_elem(light_a21)
    bridge.lights._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_dimmer(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.lights.initialize_elem(switch_dimmer_light)
    await bridge.devices.initialize_elem(switch_dimmer_light)
    bridge.lights._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
    [
        (light_a21, [light_a21_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.lights.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        bridge.lights._initialize = True
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_turn_on(mocked_entity):
    hass, entry, bridge = mocked_entity
    bridge.lights._items[light_a21.id].on.on = False
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": light_a21_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == light_a21.id


@pytest.mark.asyncio
async def test_turn_on_dimmer(mocked_dimmer):
    hass, entry, bridge = mocked_dimmer
    bridge.lights._items[switch_dimmer_light.id].on.on = False
    assert not bridge.lights._items[switch_dimmer_light.id].is_on
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": switch_dimmer_light_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == switch_dimmer_light.id
    update = payload["values"][0]
    assert update["functionClass"] == "power"
    assert update["functionInstance"] == "gang-1"
    assert update["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    switch_dimmer_update = create_devices_from_data("dimmer-HPDA1110NWBP.json")[0]
    modify_state(
        switch_dimmer_update,
        HubspaceState(
            functionClass="power",
            functionInstance="gang-1",
            value="on",
        ),
    )
    event = {
        "type": "update",
        "device_id": switch_dimmer_light.id,
        "device": switch_dimmer_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert bridge.lights._items[switch_dimmer_light.id].is_on


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    hass, entry, bridge = mocked_entity
    bridge.lights._items[light_a21.id].on.on = True
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": light_a21_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == light_a21.id


@pytest.mark.asyncio
async def test_turn_off_dimmer(mocked_dimmer):
    hass, entry, bridge = mocked_dimmer
    bridge.lights._items[switch_dimmer_light.id].on.on = True
    assert bridge.lights._items[switch_dimmer_light.id].is_on
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": switch_dimmer_light_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == switch_dimmer_light.id
    update = payload["values"][0]
    assert update["functionClass"] == "power"
    assert update["functionInstance"] == "gang-1"
    assert update["value"] == "off"
    assert not bridge.lights._items[switch_dimmer_light.id].is_on
    # Now generate update event by emitting the json we've sent as incoming event
    switch_dimmer_update = create_devices_from_data("dimmer-HPDA1110NWBP.json")[0]
    modify_state(
        switch_dimmer_update,
        HubspaceState(
            functionClass="power",
            functionInstance="gang-1",
            value="off",
        ),
    )
    event = {
        "type": "update",
        "device_id": switch_dimmer_light.id,
        "device": switch_dimmer_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert not bridge.lights._items[switch_dimmer_light.id].is_on
