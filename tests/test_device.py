"""Test the integration between Home Assistant Switches and Afero devices."""

from homeassistant.helpers import device_registry as dr
import pytest

from custom_components.hubspace import const

from .utils import create_devices_from_data, hs_raw_from_dump

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a device and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([fan_zandra])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entry):
    """Ensure parent devices are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data(fan_zandra)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        device_reg = dr.async_get(hass)
        device = device_reg.async_get_device(
            identifiers={(const.DOMAIN, "2a3572cb-3fbf-4094-846e-f2ebcb10521a")}
        )
        assert device is not None
        assert device.name == "friendly-device-2"
        assert device.model == "Zandra"
        assert device.manufacturer == "Hampton Bay"
        assert device.sw_version == "1.0.0"
        assert device.connections == {
            (dr.CONNECTION_NETWORK_MAC, "abbc66b9-d102-4404-9b14-f7d62fec1d2c"),
            (dr.CONNECTION_BLUETOOTH, "cb948b76-713f-4a20-8ad4-2abc97b402c8"),
        }
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
    # Now generate update event by emitting the json we've sent as incoming event
    afero_data = hs_raw_from_dump("fan-ZandraFan.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    await hass.async_block_till_done()
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(
        identifiers={(const.DOMAIN, "2a3572cb-3fbf-4094-846e-f2ebcb10521a")}
    )
    assert device is not None


@pytest.mark.asyncio
async def test_remove_existing_device(mocked_entry):
    """Ensure devices are properly removed from Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data(fan_zandra)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        device_reg = dr.async_get(hass)
        device = device_reg.async_get_device(
            identifiers={(const.DOMAIN, "2a3572cb-3fbf-4094-846e-f2ebcb10521a")}
        )
        assert device is not None
        # Poll when the device is missing
        await bridge.generate_events_from_data([])
        await bridge.async_block_until_done()
        await hass.async_block_till_done()
        assert len(bridge.devices.items) == 0
        await hass.async_block_till_done()
        device_reg = dr.async_get(hass)
        device = device_reg.async_get_device(
            identifiers={(const.DOMAIN, "2a3572cb-3fbf-4094-846e-f2ebcb10521a")}
        )
        assert device is None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_remove_on_startup(mocked_entry):
    """Ensure previously tracked devices are properly removed from Home Assistant."""
    hass, entry, bridge = mocked_entry
    device_reg = dr.async_get(hass)
    device_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(const.DOMAIN, "cool-beans")},
        name="name",
    )
    await hass.config_entries.async_setup(entry.entry_id)
    device = device_reg.async_get_device(identifiers={(const.DOMAIN, "cool-beans")})
    assert device is None
