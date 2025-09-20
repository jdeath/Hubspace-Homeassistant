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

alarm_panel = create_devices_from_data("security-system.json")
alarm_panel_id = "alarm_control_panel.helms_deep_securitysystem"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Alarm Panel and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data(alarm_panel)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


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
async def test_alarm_state(panel_state, expected, mocked_entry):
    """Ensure a proper mapping between Hubspace and Home Assistant."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    alarm_panel = create_devices_from_data("security-system.json")[1]
    modify_state(
        alarm_panel,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=panel_state,
        ),
    )
    await bridge.generate_devices_from_data([alarm_panel])
    await bridge.async_block_until_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
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
    afero_data = hs_raw_from_dump("security-system.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 5
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    expected_entities = [alarm_panel_id]
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


def enable_sensors(dev):
    """Ensure all sensors are in an enabled state."""
    for state in dev.states:
        if state.functionClass not in ["sensor-state"] or state.value is None:
            continue
        state.value = {
            "security-sensor-state": {
                "deviceType": 1,
                "tampered": 0,
                "triggered": 0,
                "missing": 0,
                "versionBuild": 3,
                "versionMajor": 2,
                "versionMinor": 0,
                "batteryLevel": 100,
            }
        }


async def setup_and_test_state(
    hass,
    entry,
    bridge,
    service_call,
    starting_state,
    expected_resp_state,
    expected_starting_state,
    expected_state,
    mocker,
):
    """Set up the entry and verify the alarm panel state."""
    # Setup the alarm panel to be in a different state than expected
    changed_alarm_panel = create_devices_from_data("security-system.json")[1]
    modify_state(
        changed_alarm_panel,
        AferoState(
            functionClass="alarm-state",
            functionInstance=None,
            value=starting_state,
        ),
    )
    enable_sensors(changed_alarm_panel)
    await bridge.generate_devices_from_data([changed_alarm_panel])
    await hass.config_entries.async_setup(entry.entry_id)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == expected_starting_state
    # Setup the response after disarm
    new_states = [
        AferoState(
            functionClass="alarm-state",
            value=expected_resp_state,
            lastUpdateTime=0,
            functionInstance=None,
        ),
    ]
    for state in new_states:
        modify_state(changed_alarm_panel, state)
    mocker.patch.object(
        bridge, "fetch_device_states", return_value=changed_alarm_panel.states
    )
    mocker.patch("aioafero.v1.controllers.security_system.UPDATE_TIME", 0)
    # Execute the test
    call_args = {"entity_id": alarm_panel_id}
    if service_call == "alarm_disarm":
        call_args["code"] = "1234"
    await hass.services.async_call(
        "alarm_control_panel",
        service_call,
        call_args,
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(alarm_panel_id)
    assert entity is not None
    assert entity.state == expected_state


@pytest.mark.asyncio
async def test_service_alarm_disarm(mocked_entry, mocker):
    """Ensure the service call alarm_disarm works as expected."""
    await setup_and_test_state(
        mocked_entry[0],
        mocked_entry[1],
        mocked_entry[2],
        "alarm_disarm",
        "arm-away",
        "disarmed",
        AlarmControlPanelState.ARMED_AWAY,
        AlarmControlPanelState.DISARMED,
        mocker,
    )


@pytest.mark.asyncio
async def test_service_alarm_arm_home(mocked_entry, mocker):
    """Ensure the service call alarm_arm_home works as expected."""
    await setup_and_test_state(
        mocked_entry[0],
        mocked_entry[1],
        mocked_entry[2],
        "alarm_arm_home",
        "disarmed",
        "arm-started-stay",
        AlarmControlPanelState.DISARMED,
        AlarmControlPanelState.ARMING,
        mocker,
    )


@pytest.mark.asyncio
async def test_service_alarm_arm_away(mocked_entry, mocker):
    """Ensure the service call alarm_arm_away works as expected."""
    await setup_and_test_state(
        mocked_entry[0],
        mocked_entry[1],
        mocked_entry[2],
        "alarm_arm_away",
        "disarmed",
        "arm-started-away",
        AlarmControlPanelState.DISARMED,
        AlarmControlPanelState.ARMING,
        mocker,
    )


@pytest.mark.asyncio
async def test_service_alarm_trigger(mocked_entry, mocker):
    """Ensure the service call alarm_trigger works as expected."""
    await setup_and_test_state(
        mocked_entry[0],
        mocked_entry[1],
        mocked_entry[2],
        "alarm_trigger",
        "disarmed",
        "alarming-sos",
        AlarmControlPanelState.DISARMED,
        AlarmControlPanelState.TRIGGERED,
        mocker,
    )
