import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
)

from custom_components.hubspace import light

from .utils import create_devices_from_data

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]

switch_dimmer = create_devices_from_data("switch-HPDA311CWB.json")
switch_dimmer_light = switch_dimmer[0]


@pytest.fixture
def empty_light(mocked_coordinator):
    yield light.HubspaceLight(mocked_coordinator, "test light")


@pytest.fixture
def temperature_light(mocked_coordinator):
    temp_light = light.HubspaceLight(mocked_coordinator, "test light")
    temp_light._temperature_choices = [2700, 3000, 3500]
    yield temp_light


@pytest.mark.parametrize(
    "functions, expected_attrs",
    [
        (
            fan_zandra_light.functions,
            {
                "_instance_attrs": {"power": "light-power"},
                "_color_modes": {
                    ColorMode.ONOFF,
                    ColorMode.COLOR_TEMP,
                    ColorMode.BRIGHTNESS,
                },
                "_supported_brightness": [x for x in range(1, 101)],
            },
        ),
        (
            switch_dimmer_light.functions,
            {
                "_instance_attrs": {},
                "_color_modes": {ColorMode.ONOFF, ColorMode.BRIGHTNESS},
                "_supported_brightness": [x for x in range(1, 101)],
            },
        ),
    ],
)
def test_process_functions(functions, expected_attrs, empty_light):
    empty_light.process_functions(functions)
    for key, val in expected_attrs.items():
        assert getattr(empty_light, key) == val


@pytest.mark.parametrize(
    "states, expected_attrs, extra_attrs",
    [
        (
            fan_zandra_light.states,
            {
                "_state": "on",
                "_color_temp": 3000,
                "_brightness": 114,
            },
            {
                "Child ID": None,
                "deviceId": None,
                "model": None,
            },
        )
    ],
)
def test_update_states(states, expected_attrs, extra_attrs, empty_light):
    empty_light.states = states
    empty_light.coordinator.data[fan_zandra_light.device_class][
        empty_light._child_id
    ] = empty_light
    empty_light.update_states()
    assert empty_light.extra_state_attributes == extra_attrs
    for key, val in expected_attrs.items():
        assert getattr(empty_light, key) == val


def test_name(empty_light):
    assert empty_light.name == "test light"


def test_unique_id(empty_light):
    empty_light._child_id = "beans"
    assert empty_light.unique_id == "beans"


@pytest.mark.parametrize(
    "state, expected",
    [
        ("on", True),
        ("off", False),
    ],
)
def test_is_on(state, expected, empty_light):
    empty_light._state = state
    assert empty_light.is_on == expected


def test_extra_state_attributes(mocked_coordinator):
    model = "bean model"
    device_id = "bean-123"
    child_id = "bean-123-123"
    test_fan = light.HubspaceLight(
        mocked_coordinator,
        "test light",
        model=model,
        device_id=device_id,
        child_id=child_id,
    )
    assert test_fan.extra_state_attributes == {
        "model": model,
        "deviceId": device_id,
        "Child ID": child_id,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "turn_on_kwargs, expected_attrs",
    [
        (
            {
                ATTR_BRIGHTNESS: 255,
                ATTR_COLOR_TEMP_KELVIN: 3000,
                ATTR_RGB_COLOR: (25, 50, 255),
            },
            {
                "_brightness": 255,
                "_color_temp": 3000,
                "_state": "on",
                "_rgb": light.RGB(25, 50, 255),
            },
        ),
    ],
)
async def test_async_turn_on(turn_on_kwargs, expected_attrs, temperature_light):
    await temperature_light.async_turn_on(**turn_on_kwargs)
    for key, val in expected_attrs.items():
        assert getattr(temperature_light, key) == val


@pytest.mark.asyncio
async def test_async_turn_off(empty_light):
    await empty_light.async_turn_off()
    assert empty_light._state == "off"
