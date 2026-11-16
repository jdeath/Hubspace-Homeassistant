"""Test the integration between Home Assistant Humidifiers and Afero (de)humidifiers."""

from functools import partial

from aioafero import EventType
from homeassistant.components.humidifier import (
    ATTR_AVAILABLE_MODES,
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDITY,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    ATTR_MODE,
    ATTR_TARGET_HUMIDITY_STEP,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
)
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er, translation
import pytest

from .utils import create_devices_from_data

dehumidifier = create_devices_from_data("dehumidifier.json")[0]
dehumidifier_id = "humidifier.server_closet_dehumidifier"

humidifier = create_devices_from_data("humidifier.json")[0]
humidifier_id = "humidifier.humid"
humidifier_mist_level_id = "select.humid_mist_level"
humidifier_timer_id = "number.humid_power_off_timer"


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
    assert entity.attributes[ATTR_TARGET_HUMIDITY_STEP] == 5
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
async def test_set_humidity_respects_device_range(mocked_entity):
    """Snap relative to the minimum and clamp when the range is not step-aligned."""
    hass, _, bridge = mocked_entity
    feature = bridge.dehumidifiers[dehumidifier.id].target_humidity
    feature.min, feature.max = 36, 84
    # 37 is nearest to 36 (absolute snapping would give 35, below the minimum)
    entity = await _call(hass, bridge, SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: 37})
    assert entity.attributes[ATTR_HUMIDITY] == 36
    # 84 snaps to 86 relative to the minimum; clamp back to the maximum
    entity = await _call(hass, bridge, SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: 84})
    assert entity.attributes[ATTR_HUMIDITY] == 84


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


@pytest.mark.asyncio
async def test_missing_optional_features(mocked_entity):
    """A resource without power or target humidity degrades instead of crashing."""
    hass, _, bridge = mocked_entity
    resource = bridge.dehumidifiers[dehumidifier.id]
    resource.on = None
    resource.target_humidity = None
    await bridge.dehumidifiers.emit_to_subscribers(
        EventType.RESOURCE_UPDATED, dehumidifier.id, resource
    )
    await hass.async_block_till_done()
    entity = hass.states.get(dehumidifier_id)
    assert entity.state == STATE_UNKNOWN
    assert ATTR_HUMIDITY not in entity.attributes
    assert entity.attributes[ATTR_MIN_HUMIDITY] == 0
    assert entity.attributes[ATTR_MAX_HUMIDITY] == 100
    with pytest.raises(ServiceValidationError):
        await _call(hass, bridge, SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: 50})


@pytest.fixture
async def mocked_humidifier(mocked_entry):
    """Initialize a mocked humidifier and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([humidifier])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


async def _call_humidifier(hass, bridge, domain, service, entity_id, data):
    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    return hass.states.get(entity_id)


@pytest.mark.asyncio
async def test_humidifier_async_setup_entry(mocked_humidifier):
    """Ensure humidifiers are discovered with their selects, number and state."""
    hass, _, _ = mocked_humidifier
    assert er.async_get(hass).async_get(humidifier_id) is not None
    entity = hass.states.get(humidifier_id)
    assert entity.state == STATE_ON
    assert entity.attributes[ATTR_DEVICE_CLASS] == "humidifier"
    assert entity.attributes[ATTR_HUMIDITY] == 60
    assert entity.attributes[ATTR_CURRENT_HUMIDITY] == 58
    assert entity.attributes[ATTR_MIN_HUMIDITY] == 30
    assert entity.attributes[ATTR_MAX_HUMIDITY] == 80
    assert entity.attributes[ATTR_TARGET_HUMIDITY_STEP] == 5
    assert entity.attributes[ATTR_MODE] == "manual"
    assert entity.attributes[ATTR_AVAILABLE_MODES] == [
        "auto",
        "manual",
        "plant-care",
        "sleep",
        "wellness",
    ]
    assert hass.states.get(humidifier_mist_level_id).state == "level-2"
    assert hass.states.get("select.humid_wellness_target").state == "wellness-sleep"
    assert hass.states.get("select.humid_plant_care_target").state == "adaptables"
    assert hass.states.get("select.humid_dark_mode").state == "off"
    assert hass.states.get(humidifier_timer_id).state == "0"


@pytest.mark.asyncio
async def test_humidifier_services(mocked_humidifier):
    """Ensure humidifier services round-trip through the controller."""
    hass, _, bridge = mocked_humidifier
    resource = bridge.humidifiers[humidifier.id]
    call = partial(_call_humidifier, hass, bridge, HUMIDIFIER_DOMAIN)
    assert (await call(SERVICE_TURN_OFF, humidifier_id, {})).state == STATE_OFF
    assert not resource.on.on
    assert (await call(SERVICE_TURN_ON, humidifier_id, {})).state == STATE_ON
    assert resource.on.on
    entity = await call(SERVICE_SET_MODE, humidifier_id, {ATTR_MODE: "auto"})
    assert entity.attributes[ATTR_MODE] == "auto"
    assert resource.mode.mode == "auto"
    entity = await call(SERVICE_SET_HUMIDITY, humidifier_id, {ATTR_HUMIDITY: 47})
    assert entity.attributes[ATTR_HUMIDITY] == 45
    assert resource.target_humidity.value == 45


@pytest.mark.asyncio
async def test_humidifier_select_and_number(mocked_humidifier):
    """Ensure the mist level select and timer number reach the controller."""
    hass, _, bridge = mocked_humidifier
    resource = bridge.humidifiers[humidifier.id]
    entity = await _call_humidifier(
        hass,
        bridge,
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        humidifier_mist_level_id,
        {ATTR_OPTION: "level-3"},
    )
    assert entity.state == "level-3"
    assert resource.selects[("atomization-level", "humidifier")].selected == "level-3"
    entity = await _call_humidifier(
        hass,
        bridge,
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        humidifier_timer_id,
        {ATTR_VALUE: 120},
    )
    assert float(entity.state) == 120
    assert resource.numbers[("power-off-timer", None)].value == 120


@pytest.mark.asyncio
async def test_humidifier_add_new_device(mocked_entry):
    """Ensure humidifiers discovered after setup are added."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(humidifier_id) is None
    await bridge.generate_devices_from_data([humidifier])
    await hass.async_block_till_done()
    assert hass.states.get(humidifier_id).state == STATE_ON


@pytest.mark.asyncio
async def test_humidifier_labels(mocked_humidifier):
    """Ensure every mode and translated select option has a display label."""
    hass, _, bridge = mocked_humidifier
    resource = bridge.humidifiers[humidifier.id]
    labels = await translation.async_get_translations(
        hass, "en", "entity", {"hubspace"}
    )
    registry = er.async_get(hass)
    assert registry.async_get(humidifier_id).translation_key == "humidifier"
    mode_prefix = "component.hubspace.entity.humidifier.humidifier.state_attributes"
    for mode in resource.mode.modes:
        assert f"{mode_prefix}.mode.state.{mode}" in labels
    expected = {
        ("atomization-level", "humidifier"): ("mist_level", "level-1", "Low"),
        ("dark-mode", None): ("dark_mode", "on", "On"),
        ("humidity", "plant-care-target"): (
            "plant_care_target",
            "tropical",
            "Tropical (75%)",
        ),
        ("humidity", "wellness-target"): (
            "wellness_target",
            "cold-flu",
            "Cold & Flu (50%)",
        ),
    }
    assert set(resource.selects) == set(expected)
    for identifier, (key, option, label) in expected.items():
        prefix = f"component.hubspace.entity.select.{key}.state"
        for select_option in resource.selects[identifier].selects:
            assert f"{prefix}.{select_option}" in labels
        assert labels[f"{prefix}.{option}"] == label
