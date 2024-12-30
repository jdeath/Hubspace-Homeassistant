import pytest
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_instance = fan_zandra[0]
fan_zandra_entity_id = "fan.friendly_device_2_fan"


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.fans.initialize_elem(fan_zandra_instance)
    await bridge.devices.initialize_elem(fan_zandra[2])
    bridge.fans._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
    [
        (fan_zandra_instance, [fan_zandra_entity_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.fans.initialize_elem(dev)
        await bridge.devices.initialize_elem(fan_zandra[2])
        bridge.fans._initialize = True
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
    bridge.fans._items[fan_zandra_instance.id].on.on = False
    await hass.services.async_call(
        "fan",
        "turn_on",
        {"entity_id": fan_zandra_entity_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == fan_zandra_instance.id


@pytest.mark.asyncio
async def test_turn_off(mocked_entity):
    hass, entry, bridge = mocked_entity
    bridge.fans._items[fan_zandra_instance.id].on.on = True
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
