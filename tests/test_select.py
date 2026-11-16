"""Test the integration between Home Assistant Selects and Afero devices."""

from aioafero import AferoState
from aioafero.errors import DeviceNotFound
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.hubspace import select
from custom_components.hubspace.const import DOMAIN

from .utils import create_devices_from_data, modify_state

exhaust_fan_from_file = create_devices_from_data("fan-exhaust-fan.json")
exhaust_fan = create_devices_from_data("fan-exhaust-fan.json")[2]
exhaust_fan_id = "select.r3_closet_humidity_sensitivity"


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
    [(exhaust_fan, [exhaust_fan_id])],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure selects are properly discovered and registered with Home Assistant."""
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
            functionClass="sensitivity",
            functionInstance="humidity-sensitivity",
            value="5-high",
        ),
    )
    await bridge.generate_devices_from_data([hs_new_dev])
    await hass.async_block_till_done()
    entity = hass.states.get("select.r3_closet_humidity_sensitivity")
    assert entity.state == "5-high"
    assert entity.attributes["options"] == [
        "1-low",
        "2-low-medium",
        "3-medium",
        "4-medium-high",
        "5-high",
    ]


@pytest.mark.asyncio
async def test_set_value(mocked_entity):
    """Ensure the service call select_option works as expected."""
    hass, _, bridge = mocked_entity
    bridge.exhaust_fans[exhaust_fan.id].selects[
        ("sensitivity", "humidity-sensitivity")
    ].selected = "3-medium"
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": exhaust_fan_id, "option": "5-high"},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(exhaust_fan_id)
    assert entity is not None
    # Test fails because this fails to update. Checking the device shows its been updated
    # and its updated in HA, but not in the test
    assert entity.state == "5-high"


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
    await bridge.generate_devices_from_data(
        create_devices_from_data("fan-exhaust-fan.json")
    )
    await hass.async_block_till_done()
    expected_entities = [exhaust_fan_id]
    entity_reg = er.async_get(hass)
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
async def test_security_sensor_select(mocked_entry):
    """Ensure selects work properly for security systems."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    alarm_panel = create_devices_from_data("security-system.json")[1]
    modify_state(
        alarm_panel,
        AferoState(
            functionClass="sensor-config",
            functionInstance="sensor-4",
            value={
                "security-sensor-config-v2": {
                    "chirpMode": 1,
                    "triggerType": 3,
                    "bypassType": 0,
                }
            },
        ),
    )
    alarm_panel = create_devices_from_data("security-system.json")[1]
    await bridge.generate_devices_from_data([alarm_panel])
    await bridge.async_block_until_done()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.helms_deep_sensor_4_can_be_bypassed", "option": "On"},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()


christmas_tree = create_devices_from_data("light-christmas-tree.json")[0]
tree_brightness_id = "select.christmas_tree_brightness"


@pytest.fixture
async def mocked_tree(mocked_entry):
    """Initialize a mocked pre-lit tree with brightness presets."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([christmas_tree])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_brightness_preset_select(mocked_tree):
    """Lights with brightness-presets get a Brightness select, dimmest first."""
    hass, _, _ = mocked_tree
    entity = hass.states.get(tree_brightness_id)
    assert entity is not None
    assert entity.state == "Low"
    assert entity.attributes["options"] == ["Low", "Medium", "High"]


@pytest.mark.asyncio
async def test_brightness_preset_select_option(mocked_tree, mocker):
    """Selecting a preset sends the raw brightness-presets value to the API."""
    hass, _, bridge = mocked_tree
    update_api = mocker.patch.object(
        bridge.lights, "update_afero_api", new=mocker.AsyncMock(return_value=False)
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": tree_brightness_id, "option": "High"},
        blocking=True,
    )
    await bridge.async_block_until_done()
    update_api.assert_awaited_once()
    device_id, states = update_api.await_args.args
    assert device_id == christmas_tree.id
    assert [(state["functionClass"], state["value"]) for state in states] == [
        ("brightness-presets", "high")
    ]


@pytest.mark.asyncio
async def test_brightness_preset_added_with_new_light(mocked_entry):
    """A light discovered after setup also gets its Brightness select."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(tree_brightness_id) is None
    await bridge.generate_devices_from_data([christmas_tree])
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get(tree_brightness_id) is not None


@pytest.mark.asyncio
async def test_brightness_preset_helpers(mocked_tree, mocker):
    """Helpers cope with untracked devices, missing state and unknown presets."""
    hass, _, bridge = mocked_tree
    hs_bridge = hass.data[DOMAIN][next(iter(hass.data[DOMAIN]))]
    assert select.get_raw_device(hs_bridge, "not-a-device") is None
    assert select.get_brightness_presets(None) == []
    assert sorted(["high", "turbo", "low"], key=select.brightness_preset_sort_key) == [
        "low",
        "high",
        "turbo",
    ]
    entity = next(
        ent
        for ent in hass.data["select"].entities
        if ent.entity_id == tree_brightness_id
    )
    device = bridge.get_afero_device(christmas_tree.id)
    device.states = [
        state
        for state in device.states
        if state.functionClass != select.BRIGHTNESS_PRESET_CLASS
    ]
    assert entity.current_option is None
    mocker.patch.object(bridge, "get_afero_device", side_effect=DeviceNotFound("gone"))
    assert entity.current_option is None
