"""Test the integration between Home Assistant Sensors and Afero devices."""

from aioafero import AferoState
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, modify_state

transformer = create_devices_from_data("transformer.json")[0]
transformer_voltage = "sensor.friendly_device_6_output_voltage_switch"
transformer_watts = "sensor.friendly_device_6_watts"
transformer_rssi = "sensor.friendly_device_6_wifi_rssi"
lock = create_devices_from_data("door-lock-TBD.json")[0]
lock_battery = "sensor.friendly_device_0_battery_level"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Switch and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.switches.initialize_elem(transformer)
    await bridge.devices.initialize_elem(transformer)
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
            transformer,
            {
                transformer_voltage: ("12", "V"),
                transformer_watts: ("0", "W"),
                transformer_rssi: ("-51", "dB"),
            },
        ),
        (lock, {lock_battery: ("80", "%")}),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure sensors are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.devices.initialize_elem(dev)
        await bridge.switches.initialize_elem(dev)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity_id, exp in expected_entities.items():
            exp_value, exp_measurement = exp
            ent = entity_reg.async_get(entity_id)
            assert ent is not None
            assert ent.unit_of_measurement == exp_measurement
            test_entity = hass.states.get(entity_id)
            assert test_entity is not None
            assert test_entity.state == exp_value
    finally:
        await bridge.close()


@pytest.mark.xfail(
    reason="Sensors show in logs but then disappear. They are persistent within HA"
)
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
    hs_new_dev = create_devices_from_data("transformer.json")[0]
    event = {
        "type": "add",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("add", event)
    await hass.async_block_till_done()
    expected_entities = [
        transformer_voltage,
        transformer_watts,
        transformer_rssi,
    ]
    entity_reg = er.async_get(hass)
    # print(entity_reg.entities)
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
async def test_update(mocked_entry):
    """Ensure updates in aioafero set the correct states within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.devices.initialize_elem(transformer)
    await bridge.switches.initialize_elem(transformer)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Now generate update event by emitting the json we've sent as incoming event
    hs_new_dev = create_devices_from_data("transformer.json")[0]
    modify_state(
        hs_new_dev,
        AferoState(
            functionClass="watts",
            functionInstance=None,
            value=66,
        ),
    )
    event = {
        "type": "update",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    sensor = hass.states.get("sensor.friendly_device_6_watts")
    assert sensor.state == "66"
