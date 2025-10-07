"""Test the integration between Home Assistant Climate and Afero devices."""

from aioafero import AferoState, TemperatureUnit
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
from homeassistant.util.unit_system import IMPERIAL_SYSTEM
import pytest

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

thermostat = create_devices_from_data("thermostat.json")[0]
thermostat_id = "climate.home_heat_thermostat"

portable_ac = create_devices_from_data("portable-ac.json")[0]
portable_ac_id = "climate.garage_ac_portableac"

portable_ac_f = create_devices_from_data("portable-ac-f.json")[0]
portable_ac_f_id = "climate.steve_ac_portableac"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked thermostat and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([thermostat])
    # Force mocked entity to support auto
    bridge.thermostats[thermostat.id].hvac_mode.supported_modes.add("auto")
    # Force mocked entity to support cool
    bridge.thermostats[thermostat.id].hvac_mode.supported_modes.add("cool")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.fixture
async def mocked_portable_ac_entity(mocked_entry):
    """Initialize a mocked thermostat and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([portable_ac])
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
        (thermostat, [thermostat_id]),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    """Ensure climates are properly discovered and registered with Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([dev])
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
        == ClimateEntityFeature.TARGET_TEMPERATURE + ClimateEntityFeature.FAN_MODE
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "dev",
        "expected_entity",
    ),
    [(portable_ac, portable_ac_id)],
)
async def test_async_setup_entry_portable_ac(dev, expected_entity, mocked_entry):
    """Ensure climates are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        await bridge.generate_devices_from_data([dev])
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        assert entity_reg.async_get(expected_entity) is not None
        entity = hass.states.get(expected_entity)
        assert entity
        assert entity.state == "auto"
        assert entity.attributes[ATTR_TEMPERATURE] == 22
        assert "hvac_action" not in entity.attributes
        assert set(entity.attributes["hvac_modes"]) == {
            HVACMode.AUTO,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
        }
        assert entity.attributes["target_temp_step"] == 0.5
        assert "fan_mode" not in entity.attributes
        assert "fan_modes" not in entity.attributes
        assert entity.attributes["current_temperature"] == 35
        assert (
            entity.attributes["supported_features"]
            == ClimateEntityFeature.TARGET_TEMPERATURE
        )
    finally:
        await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "dev",
        "expected_entity",
    ),
    [(portable_ac_f, portable_ac_f_id)],
)
async def test_async_setup_entry_portable_ac_f(dev, expected_entity, mocked_entry):
    """Ensure climates are properly discovered and registered with Home Assistant."""
    try:
        hass, entry, bridge = mocked_entry
        bridge.temperature_unit = TemperatureUnit.FAHRENHEIT
        hass.config.units = IMPERIAL_SYSTEM
        await bridge.generate_devices_from_data([dev])
        await bridge.async_block_until_done()
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        assert entity_reg.async_get(expected_entity) is not None
        entity = hass.states.get(expected_entity)
        assert entity
        assert entity.state == "auto"
        assert entity.attributes[ATTR_TEMPERATURE] == 60
        assert "hvac_action" not in entity.attributes
        assert set(entity.attributes["hvac_modes"]) == {
            HVACMode.AUTO,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
        }
        assert entity.attributes["target_temp_step"] == 1
        assert "fan_mode" not in entity.attributes
        assert "fan_modes" not in entity.attributes
        assert entity.attributes["current_temperature"] == 82
        assert (
            entity.attributes["supported_features"]
            == ClimateEntityFeature.TARGET_TEMPERATURE
        )
    finally:
        await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("file_name", "expected_entities"),
    [("thermostat.json", [thermostat_id]), ("portable-ac.json", [portable_ac_id])],
)
async def test_add_new_device(file_name, expected_entities, mocked_entry, caplog):
    """Ensure newly added devices are properly discovered and registered with Home Assistant."""
    hass, entry, bridge = mocked_entry
    assert len(bridge.devices.items) == 0
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(bridge.devices.subscribers) > 0
    assert len(bridge.devices.subscribers["*"]) > 0
    # Now generate update event by emitting the json we've sent as incoming event
    afero_data = hs_raw_from_dump(file_name)
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    entity_reg = er.async_get(hass)
    await hass.async_block_till_done()
    for entity in expected_entities:
        assert entity_reg.async_get(entity) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "starting_mode",
        "new_mode",
        "expected_call_val",
    ),
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
async def test_set_hvac_mode(starting_mode, new_mode, expected_call_val, mocked_entity):
    """Ensure the service call set_hvac_mode works as expected."""
    hass, _, bridge = mocked_entity
    bridge.thermostats[thermostat.id].hvac_mode.supported_modes = {
        "off",
        "heat",
        "auto",
        "fan",
        "cool",
    }
    bridge.thermostats[thermostat.id].hvac_mode.mode = starting_mode
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": thermostat_id, ATTR_HVAC_MODE: new_mode},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.state == new_mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "afero_mode",
        "expected",
    ),
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
    """Ensure the correct states are sent and the entity is properly updated."""
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
    await bridge.generate_devices_from_data([thermostat_update])
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity.attributes["fan_mode"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "afero_mode",
        "afero_mode_hvac",
        "expected",
    ),
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
    """Ensure the correct states are sent and the entity is properly updated."""
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
    await bridge.generate_devices_from_data([thermostat_update])
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity.attributes["hvac_action"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "afero_mode",
        "expected",
        "err_msg",
    ),
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
    """Ensure the correct states are sent and the entity is properly updated."""
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
    await bridge.generate_devices_from_data([thermostat_update])
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    if not err_msg:
        assert entity.state == expected
    else:
        assert err_msg in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "starting_mode",
        "new_mode",
    ),
    [
        (FAN_ON, "on"),
        ("off", "intermittent"),
    ],
)
async def test_set_fan_mode(starting_mode, new_mode, mocked_entity):
    """Ensure the service call set_fan_mode works as expected."""
    hass, _, bridge = mocked_entity
    bridge.thermostats[thermostat.id].hvac_mode.mode = starting_mode
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": thermostat_id, "fan_mode": new_mode},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.attributes["fan_mode"] == new_mode


@pytest.mark.asyncio
async def test_set_temperature(mocked_entity):
    """Ensure the service call set_temperature works as expected."""
    hass, _, bridge = mocked_entity
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": thermostat_id,
            ATTR_TEMPERATURE: 12,
            ATTR_TARGET_TEMP_HIGH: 27,
            ATTR_TARGET_TEMP_LOW: 13,
            ATTR_HVAC_MODE: HVACMode.COOL,
        },
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(thermostat_id)
    assert entity is not None
    assert entity.state == HVACMode.COOL
    assert entity.attributes[ATTR_TARGET_TEMP_HIGH] == 27.0
    assert entity.attributes[ATTR_TARGET_TEMP_LOW] == 13.0
    assert entity.attributes[ATTR_TEMPERATURE] == 12.0


@pytest.mark.asyncio
async def test_set_temperature_portable_ac(mocked_portable_ac_entity):
    """Ensure the service call set_temperature works as expected."""
    hass, _, bridge = mocked_portable_ac_entity
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": portable_ac_id,
            ATTR_TEMPERATURE: 25,
            ATTR_HVAC_MODE: HVACMode.DRY,
        },
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    entity = hass.states.get(portable_ac_id)
    assert entity is not None
    assert entity.state == HVACMode.DRY
    assert entity.attributes[ATTR_TEMPERATURE] is None
