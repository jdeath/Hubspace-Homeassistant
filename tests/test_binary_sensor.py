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
            [
                "binary_sensor.friendly_device_0_error_mcu_communication_failure",
                "binary_sensor.friendly_device_0_error_fridge_high_temperature_alert",
                "binary_sensor.friendly_device_0_error_freezer_high_temperature_alert",
                "binary_sensor.friendly_device_0_error_temperature_sensor_failure",
            ],
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.devices.initialize_elem(dev)
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()
