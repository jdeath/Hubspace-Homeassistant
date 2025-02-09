import pytest
from aiohubspace import HubspaceState
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data, modify_state

transformer = create_devices_from_data("transformer.json")[0]
transformer_entity_zone_1 = "switch.friendly_device_6_zone_1"
transformer_entity_zone_2 = "switch.friendly_device_6_zone_2"
transformer_entity_zone_3 = "switch.friendly_device_6_zone_3"
hs_switch = create_devices_from_data("switch-HPSA11CWB.json")[0]
hs_switch_id = "switch.basement_furnace_switch"


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.switches.initialize_elem(hs_switch)
    await bridge.devices.initialize_elem(hs_switch)
    bridge.switches._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_entity_toggled(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.switches.initialize_elem(transformer)
    await bridge.devices.initialize_elem(transformer)
    bridge.switches._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
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
    try:
        hass, entry, bridge = mocked_entry
        await bridge.switches.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        bridge.switches._initialize = True
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_turn_on_toggle(mocked_entity_toggled):
    hass, _, bridge = mocked_entity_toggled
    assert not bridge.switches._items[transformer.id].on["zone-3"].on
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
    transformer_update = create_devices_from_data("transformer.json")[0]
    modify_state(
        transformer_update,
        HubspaceState(
            functionClass="toggle",
            functionInstance="zone-3",
            value="on",
        ),
    )
    event = {
        "type": "update",
        "device_id": transformer.id,
        "device": transformer_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert bridge.switches._items[transformer_update.id].on["zone-3"].on


@pytest.mark.asyncio
async def test_turn_on(mocked_entity):
    hass, _, bridge = mocked_entity
    assert not bridge.switches._items[hs_switch.id].on[None].on
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
    hs_switch_update = create_devices_from_data("switch-HPSA11CWB.json")[0]
    modify_state(
        hs_switch_update,
        HubspaceState(
            functionClass="toggle",
            functionInstance=None,
            value="on",
        ),
    )
    event = {
        "type": "update",
        "device_id": transformer.id,
        "device": hs_switch_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert bridge.switches._items[hs_switch_update.id].on[None].on
    assert hass.states.get(hs_switch_id).state == "on"


@pytest.mark.asyncio
async def test_turn_off_toggle(mocked_entity_toggled):
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
        HubspaceState(
            functionClass="toggle",
            functionInstance="zone-2",
            value="off",
        ),
    )
    event = {
        "type": "update",
        "device_id": transformer.id,
        "device": transformer_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert not bridge.switches._items[transformer_update.id].on["zone-2"].on


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    hass, _, bridge = mocked_entity
    bridge.switches._items[hs_switch.id].on[None].on = True
    assert bridge.switches._items[hs_switch.id].on[None].on
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
        HubspaceState(
            functionClass="toggle",
            functionInstance=None,
            value="off",
        ),
    )
    event = {
        "type": "update",
        "device_id": transformer.id,
        "device": hs_switch_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    assert not bridge.switches._items[hs_switch_update.id].on[None].on
    test_switch = hass.states.get(hs_switch_id)
    assert test_switch is not None
    assert test_switch.state == "off"


@pytest.mark.asyncio
async def test_add_new_device(mocked_entry):
    hass, entry, bridge = mocked_entry
    assert len(bridge.devices.items) == 0
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices._subscribers) > 0
    assert len(bridge.devices._subscribers["*"]) > 0
    # Now generate update event by emitting the json we've sent as incoming event
    hs_new_dev = create_devices_from_data("transformer.json")[0]
    event = {
        "type": "add",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("add", event)
    await hass.async_block_till_done()
    expected_entities = [
        transformer_entity_zone_1,
        transformer_entity_zone_2,
        transformer_entity_zone_3,
    ]
    entity_reg = er.async_get(hass)
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None
