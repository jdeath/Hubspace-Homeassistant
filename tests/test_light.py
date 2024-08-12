import copy

import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
)
from hubspace_async import HubSpaceDevice, HubSpaceState

from custom_components.hubspace import light

from .utils import create_devices_from_data

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]

switch_dimmer = create_devices_from_data("switch-HPDA311CWB.json")
switch_dimmer_light = switch_dimmer[0]

rgb_temp_light = create_devices_from_data("light-rgb_temp.json")[0]
light_a21 = create_devices_from_data("light-a21.json")[0]


def modify_state(device: HubSpaceDevice, new_state):
    for ind, state in enumerate(device.states):
        if state.functionClass != new_state.functionClass:
            continue
        if (
            new_state.functionInstance
            and new_state.functionInstance != state.functionInstance
        ):
            continue
        device.states[ind] = new_state
        break


light_a21_mode_change = copy.deepcopy(light_a21)
a21_state_rgb = HubSpaceState(
    functionClass="color-mode",
    value="color",
    lastUpdateTime=1234,
    functionInstance=None,
)
modify_state(light_a21_mode_change, a21_state_rgb)

light_a21_effect = copy.deepcopy(light_a21)
modify_state(light_a21_effect, a21_state_rgb)
a21_state_effect = HubSpaceState(
    functionClass="color-sequence",
    value="rainbow",
    lastUpdateTime=12345,
    functionInstance="custom",
)
a21_state_mode = HubSpaceState(
    functionClass="color-mode",
    value="sequence",
    lastUpdateTime=12345,
    functionInstance=None,
)
modify_state(light_a21_effect, a21_state_effect)
modify_state(light_a21_effect, a21_state_mode)


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
                "_temperature_prefix": "K",
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
        (
            rgb_temp_light.functions,
            {
                "_instance_attrs": {},
                "_color_modes": {
                    ColorMode.ONOFF,
                    ColorMode.BRIGHTNESS,
                    ColorMode.RGB,
                    ColorMode.COLOR_TEMP,
                },
                "_supported_brightness": [x for x in range(1, 101)],
                "_temperature_choices": [x for x in range(2200, 6501, 100)],
                "_temperature_prefix": "",
            },
        ),
        (
            light_a21.functions,
            {
                "_instance_attrs": {},
                "_color_modes": {
                    ColorMode.ONOFF,
                    ColorMode.BRIGHTNESS,
                    ColorMode.RGB,
                    ColorMode.COLOR_TEMP,
                },
                "_supported_brightness": [x for x in range(1, 101)],
                "_temperature_choices": [x for x in range(2200, 6501, 100)],
                "_temperature_prefix": "",
                "_effects": {
                    "custom": [
                        "chill",
                        "christmas",
                        "clarity",
                        "dinner-party",
                        "focus",
                        "getting-ready",
                        "july-4th",
                        "moonlight",
                        "nightlight",
                        "rainbow",
                        "sleep",
                        "valentines-day",
                        "wake-up",
                    ],
                    "preset": [
                        "custom",
                        "fade-3",
                        "fade-7",
                        "flash",
                        "jump-3",
                        "jump-7",
                    ],
                },
            },
        ),
    ],
)
def test_process_functions(functions, expected_attrs, empty_light):
    empty_light.process_functions(functions)
    for key, val in expected_attrs.items():
        assert getattr(empty_light, key) == val


@pytest.mark.parametrize(
    "states, expected",
    [
        # color-mode not present
        (fan_zandra_light.states, None),
        # color-mode is present, use the value
        (light_a21_mode_change.states, "color"),
    ],
)
def test_get_hs_mode(states, expected, empty_light):
    assert empty_light.get_hs_mode(states) == expected


@pytest.mark.parametrize(
    "device, expected",
    [
        # no color-mode but COLOR_TEMP is supported
        (
            fan_zandra_light,
            {"_color_mode": ColorMode.COLOR_TEMP, "_current_effect": None},
        ),
        # RGB
        (
            light_a21_mode_change,
            {"_color_mode": ColorMode.RGB, "_current_effect": None},
        ),
        # white - white isn't implemented so its temp
        (light_a21, {"_color_mode": ColorMode.COLOR_TEMP, "_current_effect": None}),
        # effect
        (
            light_a21_effect,
            {"_color_mode": ColorMode.BRIGHTNESS, "_current_effect": "rainbow"},
        ),
    ],
)
def test_determine_states_from_hs_mode(device, expected, mocker, empty_light):
    empty_light.process_functions(device.functions)
    assert empty_light.determine_states_from_hs_mode(device.states) == expected


@pytest.mark.parametrize(
    "states, expected_attrs, extra_attrs",
    [
        (
            fan_zandra_light.states,
            {
                "_state": "on",
                "_color_temp": 3000,
                "_brightness": 114,
                "_availability": True,
            },
            {
                "Child ID": None,
                "deviceId": None,
                "model": None,
            },
        ),
        # Switch from white to RGB
        (
            light_a21_mode_change.states,
            {
                "_state": "on",
                "_color_temp": 4000,
                "_brightness": 127,
                "_availability": True,
                "_color_mode": light.ColorMode.RGB,
                "_current_effect": None,
            },
            {},
        ),
        # set current effect
        (
            light_a21_effect.states,
            {
                "_state": "on",
                "_color_temp": 4000,
                "_brightness": 127,
                "_availability": True,
                "_current_effect": "rainbow",
                "_color_mode": light.ColorMode.BRIGHTNESS,
            },
            {},
        ),
    ],
)
def test_update_states(states, expected_attrs, extra_attrs, empty_light, mocker):
    mocker.patch.object(empty_light, "get_device_states", return_value=states)
    empty_light.update_states()
    if extra_attrs:
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
    "device, effect, expected",
    [
        # Preset state
        (
            light_a21,
            "fade-3",
            [
                HubSpaceState(
                    functionClass="color-sequence",
                    functionInstance="preset",
                    value="fade-3",
                ),
            ],
        ),
        # custom state
        (
            light_a21,
            "getting-ready",
            [
                HubSpaceState(
                    functionClass="color-sequence",
                    functionInstance="preset",
                    value="custom",
                ),
                HubSpaceState(
                    functionClass="color-sequence",
                    functionInstance="custom",
                    value="getting-ready",
                ),
            ],
        ),
    ],
)
async def test_determine_effect_states(device, effect, expected, empty_light):
    empty_light.process_functions(device.functions)
    res = await empty_light.determine_effect_states(effect)
    assert len(res) == len(expected)
    for ind, state in enumerate(res):
        assert state == expected[ind]


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
