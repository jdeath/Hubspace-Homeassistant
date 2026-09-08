"""Test the integration between Home Assistant Humidifiers and Afero dehumidifiers."""

from homeassistant.components.humidifier import (
    ATTR_AVAILABLE_MODES,
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDITY,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    ATTR_MODE,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data

dehumidifier = create_devices_from_data("dehumidifier.json")[0]
dehumidifier_id = "humidifier.server_closet_dehumidifier"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked dehumidifier and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([dehumidifier])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


async def _call(hass, bridge, service, data):
    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        service,
        {ATTR_ENTITY_ID: dehumidifier_id, **data},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    return hass.states.get(dehumidifier_id)


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entity):
    """Ensure dehumidifiers are discovered with their selects and state."""
    hass, _, _ = mocked_entity
    assert er.async_get(hass).async_get(dehumidifier_id) is not None
    entity = hass.states.get(dehumidifier_id)
    assert entity is not None
    assert entity.state == STATE_ON
    assert entity.attributes[ATTR_DEVICE_CLASS] == "dehumidifier"
    assert entity.attributes[ATTR_HUMIDITY] == 40
    assert entity.attributes[ATTR_CURRENT_HUMIDITY] == 48
    assert entity.attributes[ATTR_MIN_HUMIDITY] == 35
    assert entity.attributes[ATTR_MAX_HUMIDITY] == 85
    assert entity.attributes[ATTR_MODE] == "set"
    assert entity.attributes[ATTR_AVAILABLE_MODES] == [
        "comfort",
        "continuous",
        "dryer",
        "set",
    ]
    assert hass.states.get("select.server_closet_dehumidifier_pump").state == "on"
    assert (
        hass.states.get("select.server_closet_dehumidifier_fan_speed").state
        == "fan-speed-2-100"
    )


@pytest.mark.asyncio
async def test_turn_off_on(mocked_entity):
    """Ensure turn_off / turn_on round-trip through the controller."""
    hass, _, bridge = mocked_entity
    assert (await _call(hass, bridge, SERVICE_TURN_OFF, {})).state == STATE_OFF
    assert not bridge.dehumidifiers[dehumidifier.id].on.on
    assert (await _call(hass, bridge, SERVICE_TURN_ON, {})).state == STATE_ON
    assert bridge.dehumidifiers[dehumidifier.id].on.on


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested", "expected"),
    [(50, 50), (42, 40), (43, 45)],
)
async def test_set_humidity(mocked_entity, requested, expected):
    """Ensure the target humidity is snapped to the unit's step."""
    hass, _, bridge = mocked_entity
    entity = await _call(hass, bridge, SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: requested})
    assert entity.attributes[ATTR_HUMIDITY] == expected
    assert bridge.dehumidifiers[dehumidifier.id].target_humidity.value == expected


@pytest.mark.asyncio
async def test_set_mode(mocked_entity):
    """Ensure set_mode round-trips through the controller."""
    hass, _, bridge = mocked_entity
    entity = await _call(hass, bridge, SERVICE_SET_MODE, {ATTR_MODE: "continuous"})
    assert entity.attributes[ATTR_MODE] == "continuous"
    assert bridge.dehumidifiers[dehumidifier.id].mode.mode == "continuous"


@pytest.mark.asyncio
async def test_add_new_device(mocked_entry):
    """Ensure dehumidifiers discovered after setup are added."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(dehumidifier_id) is None
    await bridge.generate_devices_from_data([dehumidifier])
    await hass.async_block_till_done()
    assert hass.states.get(dehumidifier_id).state == STATE_ON
