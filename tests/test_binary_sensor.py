import pytest
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data

freezer = create_devices_from_data("freezer.json")[0]


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.devices.initialize_elem(freezer)
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
            freezer,
            {
                "binary_sensor.friendly_device_0_mcu_communication_failure": "off",
                "binary_sensor.friendly_device_0_fridge_high_temp_alert": "on",
                "binary_sensor.friendly_device_0_freezer_high_temp_alert": "off",
                "binary_sensor.friendly_device_0_sensor_failure": "off",
            },
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry, caplog):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.devices.initialize_elem(dev)
        bridge.devices._initialize = True
        # Add in a bad sensor
        bridge.devices._items[freezer.id].binary_sensors["bad_sensor"] = {}
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        for entity, exp_value in expected_entities.items():
            ent = hass.states.get(entity)
            assert ent is not None, f"Unable to find entity {entity}"
            assert ent.state == exp_value, f"Unexpected value on {entity}"
        assert (
            f"Unknown sensor bad_sensor found in {freezer.id}. Please open a bug report"
            in caplog.text
        )
    finally:
        await bridge.close()


@pytest.mark.xfail(reason="Sensors show in logs but then disappear. They are persistent within HA")
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
    hs_new_dev = create_devices_from_data("freezer.json")[0]
    event = {
        "type": "add",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("add", event)
    await hass.async_block_till_done()
    expected_binary_sensors = [
        "binary_sensor.friendly_device_0_mcu_communication_failure",
        "binary_sensor.friendly_device_0_fridge_high_temp_alert",
        "binary_sensor.friendly_device_0_freezer_high_temp_alert",
        "binary_sensor.friendly_device_0_sensor_failure",
    ]
    entity_reg = er.async_get(hass)
    for binary_sensor in expected_binary_sensors:
        assert (
            entity_reg.async_get(binary_sensor) is not None
        ), f"Unable to find entity {binary_sensor}"
