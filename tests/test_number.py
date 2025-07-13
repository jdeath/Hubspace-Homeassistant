"""Test the integration between Home Assistant Numbers and Afero devices."""

from aioafero import AferoState
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, modify_state

exhaust_fan_from_file = create_devices_from_data("fan-exhaust-fan.json")
exhaust_fan = exhaust_fan_from_file[2]
exhaust_fan_number_id = "number.r3_closet_auto_off_timer"


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
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == exhaust_fan.id
    assert len(payload["values"]) == 1
    payload = payload["values"][0]
    assert payload["functionClass"] == "auto-off-timer"
    assert payload["functionInstance"] == "auto-off"
    assert payload["value"] == 120
    # Now generate update event by emitting the json we've sent as incoming event
    hs_device_update = create_devices_from_data("fan-exhaust-fan.json")[2]
    modify_state(
        hs_device_update,
        AferoState(
            functionClass="auto-off-timer",
            functionInstance="auto-off",
            value=120,
        ),
    )
    await bridge.generate_devices_from_data([hs_device_update])
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
