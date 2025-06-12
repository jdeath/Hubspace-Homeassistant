"""Test the integration between Home Assistant Switches and Afero devices."""

from aioafero import AferoState
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, modify_state

alarm_panel = create_devices_from_data("security-system.json")[1]
alarm_panel_id = "alarm_control_panel.helms_deep_securitysystem"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Switch and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.security_systems.initialize_elem(alarm_panel)
    await bridge.devices.initialize_elem(alarm_panel)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entry):
    """Ensure switches are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.security_systems.initialize_elem(alarm_panel)
        await bridge.devices.initialize_elem(alarm_panel)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        assert entity_reg.async_get(alarm_panel_id) is not None
        entity = hass.states.get(alarm_panel_id)
        assert entity.state == AlarmControlPanelState.DISARMED
        assert entity.attributes["code_format"] == CodeFormat.NUMBER
        assert entity.attributes["code_arm_required"] is False
        expected = (
            AlarmControlPanelEntityFeature.ARM_AWAY
            + AlarmControlPanelEntityFeature.ARM_HOME
            + AlarmControlPanelEntityFeature.TRIGGER
        )
        assert entity.attributes["supported_features"] == expected
    finally:
        await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("panel_state", "expected"),
    [
        ("arm-away", AlarmControlPanelState.ARMED_AWAY),
        ("alarming", AlarmControlPanelState.TRIGGERED),
        ("alarming-sos", AlarmControlPanelState.TRIGGERED),
        ("arm-stay", AlarmControlPanelState.ARMED_HOME),
        ("arm-started-stay", AlarmControlPanelState.ARMING),
        ("disarmed", AlarmControlPanelState.DISARMED),
        ("triggered", AlarmControlPanelState.PENDING),
        ("arm-started-away", AlarmControlPanelState.ARMING),
    ],
)
async def test_alarm_state(panel_state, expected, mocked_entry):
    """Ensure a proper mapping between Hubspace and Home Assistant."""
    hass, entry, bridge = mocked_entry
    alarm_panel = create_devices_from_data("security-system.json")[1]
    modify_state(
        alarm_panel,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=panel_state,
        ),
    )
    await bridge.security_systems.initialize_elem(alarm_panel)
    await bridge.devices.initialize_elem(alarm_panel)
    await hass.config_entries.async_setup(entry.entry_id)
    entity = hass.states.get(alarm_panel_id)
    assert entity.state == expected


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
    hs_new_dev = create_devices_from_data("security-system.json")[1]
    event = {
        "type": "add",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("add", event)
    await hass.async_block_till_done()
    entity_reg = er.async_get(hass)
    assert entity_reg.async_get(alarm_panel_id) is not None


@pytest.mark.asyncio
async def test_service_alarm_disarm(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    expected_state = "disarmed"
    bridge.security_systems[alarm_panel.id].alarm_state.mode = "armed-away"
    await hass.services.async_call(
        "alarm_control_panel",
        "alarm_disarm",
        {"entity_id": alarm_panel_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == alarm_panel.id
    update = payload["values"][0]
    assert update["functionClass"] == "alarm-state"
    assert update["functionInstance"] is None
    assert update["value"] == expected_state
    # Now generate update event by emitting the json we've sent as incoming event
    entity_update = create_devices_from_data("security-system.json")[1]
    modify_state(
        alarm_panel,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=expected_state,
        ),
    )
    event = {
        "type": "update",
        "device_id": alarm_panel.id,
        "device": entity_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == AlarmControlPanelState.DISARMED


@pytest.mark.asyncio
async def test_service_alarm_arm_home(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    expected_state = "arm-started-stay"
    await hass.services.async_call(
        "alarm_control_panel",
        "alarm_arm_home",
        {"entity_id": alarm_panel_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == alarm_panel.id
    update = payload["values"][0]
    assert update["functionClass"] == "alarm-state"
    assert update["functionInstance"] is None
    assert update["value"] == expected_state
    # Now generate update event by emitting the json we've sent as incoming event
    entity_update = create_devices_from_data("security-system.json")[1]
    modify_state(
        entity_update,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=expected_state,
        ),
    )
    event = {
        "type": "update",
        "device_id": alarm_panel.id,
        "device": entity_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == AlarmControlPanelState.ARMING


@pytest.mark.asyncio
async def test_service_alarm_arm_away(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    expected_state = "arm-started-away"
    await hass.services.async_call(
        "alarm_control_panel",
        "alarm_arm_away",
        {"entity_id": alarm_panel_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == alarm_panel.id
    update = payload["values"][0]
    assert update["functionClass"] == "alarm-state"
    assert update["functionInstance"] is None
    assert update["value"] == expected_state
    # Now generate update event by emitting the json we've sent as incoming event
    entity_update = create_devices_from_data("security-system.json")[1]
    modify_state(
        entity_update,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=expected_state,
        ),
    )
    event = {
        "type": "update",
        "device_id": alarm_panel.id,
        "device": entity_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == AlarmControlPanelState.ARMING


@pytest.mark.asyncio
async def test_service_alarm_trigger(mocked_entity):
    """Ensure the service call turn_on works as expected."""
    hass, _, bridge = mocked_entity
    expected_state = "alarming-sos"
    await hass.services.async_call(
        "alarm_control_panel",
        "alarm_trigger",
        {"entity_id": alarm_panel_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == alarm_panel.id
    update = payload["values"][0]
    assert update["functionClass"] == "alarm-state"
    assert update["functionInstance"] is None
    assert update["value"] == expected_state
    # Now generate update event by emitting the json we've sent as incoming event
    entity_update = create_devices_from_data("security-system.json")[1]
    modify_state(
        entity_update,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=expected_state,
        ),
    )
    event = {
        "type": "update",
        "device_id": alarm_panel.id,
        "device": entity_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == AlarmControlPanelState.TRIGGERED
