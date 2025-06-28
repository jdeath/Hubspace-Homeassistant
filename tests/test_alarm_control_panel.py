"""Test the integration between Home Assistant Switches and Afero devices."""

from aioafero import AferoState
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

alarm_panel = create_devices_from_data("security-system.json")[1]
alarm_panel_id = "alarm_control_panel.helms_deep_securitysystem"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Alarm Panel and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    # Now generate update event by emitting the json we've sent as incoming event
    afero_data = hs_raw_from_dump("security-system.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    return mocked_entry


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entity):
    """Ensure switches are properly discovered and registered with Home Assistant."""
    hass, entry, bridge = mocked_entity
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
async def test_alarm_state(panel_state, expected, mocked_entity):
    """Ensure a proper mapping between Hubspace and Home Assistant."""
    hass, entry, bridge = mocked_entity
    alarm_panel = create_devices_from_data("security-system.json")[1]
    modify_state(
        alarm_panel,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=panel_state,
        ),
    )

    event = {
        "type": "update",
        "device_id": alarm_panel.id,
        "device": alarm_panel,
    }
    bridge.emit_event("update", event)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == expected


@pytest.mark.asyncio
async def test_add_new_device(mocked_entity):
    """Ensure newly added devices are properly discovered and registered with Home Assistant."""
    hass, _, _ = mocked_entity
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
