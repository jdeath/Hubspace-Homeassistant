import pytest
from aioafero import AferoState
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    FAN_OFF,
    FAN_ON,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data, modify_state

thermostat = create_devices_from_data("thermostat.json")[0]
thermostat_id = "climate.home_heat_thermostat"


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.thermostats.initialize_elem(thermostat)
    await bridge.devices.initialize_elem(thermostat)
    bridge.thermostats._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
    [
        (thermostat, [thermostat_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.thermostats.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        bridge.thermostats._initialize = True
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
        entity = hass.states.get(thermostat_id)
        assert entity is not None
        assert entity.state == "heat"
        assert entity.attributes[ATTR_TEMPERATURE] == 18
        assert entity.attributes["hvac_action"] == "off"
        assert set(entity.attributes["hvac_modes"]) == {
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
            HVACMode.OFF,
        }
        assert entity.attributes["target_temp_step"] == 0.5
        assert entity.attributes["fan_mode"] == "auto"
        assert set(entity.attributes["fan_modes"]) == {"auto", "intermittent", "on"}
        assert entity.attributes["current_temperature"] == 18.3
        assert (
            entity.attributes["supported_features"]
            == ClimateEntityFeature.TARGET_TEMPERATURE
            + ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            + ClimateEntityFeature.FAN_MODE
        )
    finally:
        await bridge.close()


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
    hs_new_dev = create_devices_from_data("thermostat.json")[0]
    event = {
        "type": "add",
        "device_id": hs_new_dev.id,
        "device": hs_new_dev,
    }
    bridge.emit_event("add", event)
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    expected_entities = [thermostat_id]
    entity_reg = er.async_get(hass)
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "starting_mode,new_mode,expected_call_val",
    [
        (
            "heat",
            HVACMode.COOL,
            "cool",
        ),
        (
            "cool",
            HVACMode.HEAT,
            "heat",
        ),
        (
            "cool",
            HVACMode.HEAT_COOL,
            "auto",
        ),
        (
            "cool",
            HVACMode.OFF,
            "off",
        ),
        (
            "cool",
            HVACMode.FAN_ONLY,
            "fan",
        ),
    ],
)
async def test_set_hvac_mode(
    starting_mode, new_mode, expected_call_val, mocked_entity
):
    hass, _, bridge = mocked_entity
    bridge.thermostats._items[thermostat.id].hvac_mode.mode = starting_mode
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": thermostat_id, ATTR_HVAC_MODE: new_mode},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == thermostat.id
    update = payload["values"][0]
    assert update["value"] == expected_call_val
    # Now generate update event by emitting the json we've sent as incoming event
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="mode",
            functionInstance=None,
            value=expected_call_val,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.state == new_mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "afero_mode,expected",
    [
        (
            "on",
            FAN_ON,
        ),
        (
            "off",
            FAN_OFF,
        ),
        (
            "intermittent",
            "intermittent",
        ),
    ],
)
async def test_fan_mode(afero_mode, expected, mocked_entity):
    hass, _, bridge = mocked_entity
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="fan-mode",
            functionInstance=None,
            value=afero_mode,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity.attributes["fan_mode"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "afero_mode,afero_mode_hvac,expected",
    [
        (
            "cooling",
            "cool",
            HVACAction.COOLING,
        ),
        (
            "heating",
            "heat",
            HVACAction.HEATING,
        ),
        (
            "fan",
            "fan",
            HVACAction.FAN,
        ),
        (
            "off",
            "off",
            HVACAction.OFF,
        ),
        (
            "bad-thing",
            "off",
            "bad-thing",
        ),
    ],
)
async def test_hvac_action(afero_mode, afero_mode_hvac, expected, mocked_entity):
    hass, _, bridge = mocked_entity
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="current-system-state",
            functionInstance=None,
            value=afero_mode,
        ),
    )
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="mode",
            functionInstance=None,
            value=afero_mode_hvac,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity.attributes["hvac_action"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "afero_mode,expected,err_msg",
    [
        ("cool", HVACMode.COOL, None),
        (
            "heat",
            HVACMode.HEAT,
            None,
        ),
        (
            "fan",
            HVACMode.FAN_ONLY,
            None,
        ),
        (
            "off",
            HVACMode.OFF,
            None,
        ),
        (
            "auto",
            HVACMode.HEAT_COOL,
            None,
        ),
        (
            "bad-thing",
            None,
            "Unknown hvac mode: bad-thing",
        ),
    ],
)
async def test_hvac_mode(afero_mode, expected, err_msg, mocked_entity, caplog):
    hass, _, bridge = mocked_entity
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="mode",
            functionInstance=None,
            value=afero_mode,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    if not err_msg:
        assert entity.state == expected
    else:
        assert err_msg in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "starting_mode, new_mode",
    [
        (FAN_ON, "on"),
        ("off", "intermittent"),
    ],
)
async def test_set_fan_mode(starting_mode, new_mode, mocked_entity):
    hass, _, bridge = mocked_entity
    bridge.thermostats._items[thermostat.id].hvac_mode.mode = starting_mode
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": thermostat_id, "fan_mode": new_mode},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == thermostat.id
    update = payload["values"][0]
    assert update["value"] == new_mode
    # Now generate update event by emitting the json we've sent as incoming event
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="fan-mode",
            functionInstance=None,
            value=new_mode,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.attributes["fan_mode"] == new_mode


@pytest.mark.asyncio
async def test_set_temperature(mocked_entity):
    hass, _, bridge = mocked_entity
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": thermostat_id,
            ATTR_TEMPERATURE: 12,
            ATTR_TARGET_TEMP_HIGH: 27,
            ATTR_TARGET_TEMP_LOW: 12,
            ATTR_HVAC_MODE: HVACMode.COOL,
        },
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == thermostat.id
    # Now generate update event by emitting the json we've sent as incoming event
    thermostat_update = create_devices_from_data("thermostat.json")[0]
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="mode",
            functionInstance=None,
            value="cool",
        ),
    )
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="temperature",
            functionInstance="cooling-target",
            value=12,
        ),
    )
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="temperature",
            functionInstance="auto-cooling-target",
            value=27,
        ),
    )
    modify_state(
        thermostat_update,
        AferoState(
            functionClass="temperature",
            functionInstance="auto-heating-target",
            value=12,
        ),
    )
    event = {
        "type": "update",
        "device_id": thermostat_update.id,
        "device": thermostat_update,
    }
    bridge.emit_event("update", event)
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.state == HVACMode.COOL
    assert entity.attributes[ATTR_TARGET_TEMP_HIGH] == 27
    assert entity.attributes[ATTR_TARGET_TEMP_LOW] == 12
