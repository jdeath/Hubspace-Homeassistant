"""Test the integration between Home Assistant Binary Sensors and Afero devices."""

from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data

freezer = create_devices_from_data("freezer.json")[0]


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked freezer and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([freezer])
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
    """Ensure Binary Sensors are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data([dev])
        # Add in a bad sensor
        bridge.devices[freezer.id].binary_sensors["bad_sensor"] = {}
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
    await bridge.generate_devices_from_data(create_devices_from_data("freezer.json"))
    await hass.async_block_till_done()
    expected_binary_sensors = [
        "binary_sensor.friendly_device_0_mcu_communication_failure",
        "binary_sensor.friendly_device_0_fridge_high_temp_alert",
        "binary_sensor.friendly_device_0_freezer_high_temp_alert",
        "binary_sensor.friendly_device_0_sensor_failure",
    ]
    entity_reg = er.async_get(hass)
    for binary_sensor in expected_binary_sensors:
        assert entity_reg.async_get(binary_sensor) is not None, (
            f"Unable to find entity {binary_sensor}"
        )
