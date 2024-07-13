import json
import os
from contextlib import suppress

import pytest
import requests
from homeassistant.components.fan import FanEntityFeature
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from hubspace_async import HubSpaceState

from custom_components.hubspace import fan
from custom_components.hubspace.const import (
    CONF_DEBUG,
    CONF_FRIENDLYNAMES,
    CONF_ROOMNAMES,
)

current_path = os.path.dirname(os.path.realpath(__file__))


with open(os.path.join(current_path, "data", "device_fan.json"), "rb") as fh:
    fan_data = json.load(fh)

with open(os.path.join(current_path, "data", "device_fan_state.json"), "rb") as fh:
    fan_data_state = json.load(fh)
    fan_data_states = []
    for state in fan_data_state["values"]:
        try:
            fan_data_states.append(HubSpaceState(**state))
        except:
            pass


process_functions_expected = (
    FanEntityFeature.PRESET_MODE
    | FanEntityFeature.SET_SPEED
    | FanEntityFeature.DIRECTION
)
with suppress(AttributeError):
    process_functions_expected |= FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF


@pytest.fixture
def empty_fan(mocked_hubspace):
    yield fan.HubspaceFan(mocked_hubspace, "test fan")


@pytest.fixture
def speed_fan(mocked_hubspace):
    test_fan = fan.HubspaceFan(mocked_hubspace, "test fan")
    test_fan._supported_features = process_functions_expected
    test_fan._fan_speeds = [
        "fan-speed-6-016",
        "fan-speed-6-033",
        "fan-speed-6-050",
        "fan-speed-6-066",
        "fan-speed-6-083",
        "fan-speed-6-100",
    ]
    yield test_fan


class Test_HubSpaceFan:

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "functions, expected_attrs",
        [
            (
                fan_data[1]["description"]["functions"],
                {
                    "_instance_attrs": {
                        "fan-speed": "fan-speed",
                        "fan-reverse": "fan-reverse",
                        "power": "fan-power",
                    },
                    "_supported_features": process_functions_expected,
                    "_preset_modes": {"comfort-breeze"},
                    "_fan_speeds": [
                        "fan-speed-6-016",
                        "fan-speed-6-033",
                        "fan-speed-6-050",
                        "fan-speed-6-066",
                        "fan-speed-6-083",
                        "fan-speed-6-100",
                    ],
                },
            )
        ],
    )
    async def test_process_functions(self, functions, expected_attrs, empty_fan):
        await empty_fan.process_functions(functions)
        for key, val in expected_attrs.items():
            assert getattr(empty_fan, key) == val

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "states, expected_attrs, extra_attrs",
        [
            (
                fan_data_states,
                {
                    "_preset_mode": "comfort-breeze",
                    "_fan_speed": "fan-speed-6-016",
                    "_current_direction": "reverse",
                    "_state": "on",
                },
                {
                    "model": None,
                    "deviceId": None,
                    "Child ID": None,
                    "wifi-ssid": "SSID0",
                    "wifi-mac-address": "fd51c93dd1d0",
                    "available": True,
                    "ble-mac-address": "cb7e997398d4",
                },
            ),
        ],
    )
    async def test_update_states(
        self, states, expected_attrs, extra_attrs, empty_fan, mocker
    ):
        empty_fan._hs.get_device_state = mocker.AsyncMock(return_value=states)
        await empty_fan.update_states()
        assert empty_fan.extra_state_attributes == extra_attrs
        for key, val in expected_attrs.items():
            assert getattr(empty_fan, key) == val

    def test_name(self, empty_fan):
        assert empty_fan.name == "test fan"

    def test_unique_id(self, empty_fan):
        empty_fan._child_id = "beans"
        assert empty_fan.unique_id == "beans_fan"

    @pytest.mark.parametrize(
        "state, expected",
        [
            ("on", True),
            ("off", False),
        ],
    )
    def test_is_on(self, state, expected, empty_fan):
        empty_fan._state = state
        assert empty_fan.is_on == expected

    def test_extra_state_attributes(self, mocked_hubspace):
        model = "bean model"
        device_id = "bean-123"
        child_id = "bean-123-123"
        test_fan = fan.HubspaceFan(
            mocked_hubspace,
            "test fan",
            model=model,
            device_id=device_id,
            child_id=child_id,
        )
        assert test_fan.extra_state_attributes == {
            "model": model,
            "deviceId": device_id,
            "Child ID": child_id,
        }

    def test_current_direction(self, empty_fan):
        empty_fan._current_direction = "reverse"
        assert empty_fan.current_direction == "reverse"

    def test_oscillating(self, empty_fan):
        assert not empty_fan.oscillating

    @pytest.mark.parametrize(
        "set_speed, expected",
        [
            # Speed not set
            (None, 0),
            # Speed is set but 000
            ("fan-speed-6-000", 0),
            # Speed is set to a value
            ("fan-speed-6-016", 16),
        ],
    )
    def test_percentage(self, set_speed, expected, speed_fan):
        speed_fan._fan_speed = set_speed
        assert speed_fan.percentage == expected

    @pytest.mark.parametrize(
        "preset, expected",
        [
            # Breeze
            ("comfort-breeze", "breeze"),
            ("not supported", None),
        ],
    )
    def test_preset_mode(self, preset, expected, empty_fan):
        empty_fan._preset_mode = preset
        assert empty_fan.preset_mode == expected

    def test_preset_modes(self, empty_fan):
        preset_modes = ["comfort-breeze"]
        empty_fan._preset_modes = preset_modes
        assert empty_fan.preset_modes == preset_modes

    def test_speed_count(self, speed_fan):
        assert speed_fan.speed_count == 6

    def test_supported_features(self, empty_fan):
        features = [1, 2, 3]
        empty_fan._supported_features = features
        assert empty_fan.supported_features == features

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "percentage, preset_mode, expected_attrs",
        [
            (
                12,
                None,
                {
                    "_fan_speed": "fan-speed-6-016",
                    "_preset_mode": None,
                },
            ),
            (
                17,
                "comfort-breeze",
                {
                    "_fan_speed": "fan-speed-6-033",
                    "_preset_mode": "breeze",
                },
            ),
        ],
    )
    async def test_async_turn_on(
        self, percentage, preset_mode, expected_attrs, speed_fan
    ):
        speed_fan._supported_features = process_functions_expected
        await speed_fan.async_turn_on(percentage=percentage, preset_mode=preset_mode)
        for key, val in expected_attrs.items():
            assert getattr(speed_fan, key) == val

    @pytest.mark.asyncio
    async def test_async_turn_off(self, empty_fan):
        await empty_fan.async_turn_off()
        assert empty_fan._state == "off"
