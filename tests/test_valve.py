import pytest
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data

spigot = create_devices_from_data("water-timer.json")[0]
spigot_1 = "valve.friendly_device_0_spigot_1"
spigot_2 = "valve.friendly_device_0_spigot_2"


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.valves.initialize_elem(spigot)
    await bridge.devices.initialize_elem(spigot)
    bridge.valves._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
    [
        (
            spigot,
            [spigot_1, spigot_2],
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.valves.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        bridge.valves._initialize = True
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_open_valve(mocked_entity):
    hass, entry, bridge = mocked_entity
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


@pytest.mark.asyncio
async def test_close_valve(mocked_entity):
    hass, entry, bridge = mocked_entity
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
