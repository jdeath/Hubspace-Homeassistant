"""Test the integration between Home Assistant Valves and Afero devices."""

from aioafero import AferoState
from homeassistant.components.valve import ATTR_CURRENT_POSITION
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

spigot = create_devices_from_data("water-timer.json")[0]
spigot_1 = "valve.friendly_device_0_spigot_1"
spigot_2 = "valve.friendly_device_0_spigot_2"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Valve and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.valves.initialize_elem(spigot)
    await bridge.devices.initialize_elem(spigot)
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
        (
            spigot,
            {spigot_1: "closed", spigot_2: "open"},
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure valves are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.valves.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity, exp_state in expected_entities.items():
            assert entity_reg.async_get(entity) is not None
            ent = hass.states.get(entity)
            assert ent.state == exp_state
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_open_valve(mocked_entity):
    """Ensure the service call open_valve works as expected."""
    hass, _, bridge = mocked_entity
    await hass.services.async_call(
        "valve",
        "open_valve",
        {"entity_id": spigot_1},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == spigot.id
    assert payload["values"][0]["functionClass"] == "toggle"
    assert payload["values"][0]["functionInstance"] == "spigot-1"
    assert payload["values"][0]["value"] == "on"
    # Now generate update event by emitting the json we've sent as incoming event
    hs_device = create_devices_from_data("water-timer.json")[0]
    modify_state(
        hs_device,
        AferoState(
            functionClass="toggle",
            functionInstance="spigot-1",
            value="on",
        ),
    )
    event = {
        "type": "update",
        "device_id": spigot.id,
        "device": hs_device,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(spigot_1)
    assert entity is not None
    assert entity.attributes[ATTR_CURRENT_POSITION] == 100
    assert entity.state == "open"


@pytest.mark.asyncio
async def test_close_valve(mocked_entity):
    """Ensure the service call close_valve works as expected."""
    hass, _, bridge = mocked_entity
    await hass.services.async_call(
        "valve",
        "close_valve",
        {"entity_id": spigot_2},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == spigot.id
    assert payload["values"][0]["functionClass"] == "toggle"
    assert payload["values"][0]["functionInstance"] == "spigot-2"
    assert payload["values"][0]["value"] == "off"
    # Now generate update event by emitting the json we've sent as incoming event
    hs_device = create_devices_from_data("water-timer.json")[0]
    modify_state(
        hs_device,
        AferoState(
            functionClass="toggle",
            functionInstance="spigot-2",
            value="off",
        ),
    )
    event = {
        "type": "update",
        "device_id": spigot.id,
        "device": hs_device,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(spigot_1)
    assert entity is not None
    assert entity.attributes[ATTR_CURRENT_POSITION] == 0
    assert entity.state == "closed"


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
    afero_data = hs_raw_from_dump("water-timer.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    for entity in [spigot_1, spigot_2]:
        assert entity_reg.async_get(entity) is not None
