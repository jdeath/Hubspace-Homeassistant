import json
import os
from unittest import mock

import pytest
import requests
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

import custom_components.hubspace.const
from custom_components.hubspace import light

MOCKED_CHILD_DATA = ["child_id", "model", "deviceId", "deviceClass"]
MOCKED_TEST_DATA = {
    "test-light-1": ["childId1", "HPPA51CWB", "some-cool-light", "light"],
    "test-switch-1": ["childId2", "HPPA51CWB", "some-cool-switch", "light"],
    "test-outlet-1": ["childId3", "HPKA315CWB", "some-cool-outlet1", "power-outlet"],
    "test-fan-driskol": ["childId4", "", "fan", "fan"],
    "test-fan-zandra": ["childId5", "ZandraFan", "fan", "fan"],
    "test-transformer-1": [
        "childId6",
        "landscape-transformer",
        "some-cool-transformer1",
        "landscape-transformer",
    ],
    "test-water-1": ["childId6", "water-timerr", "some-cool-water1", "water-timer"],
}

current_path = os.path.dirname(os.path.realpath(__file__))


with open(
    os.path.join(current_path, "data", "api_response_single_room.json"), "rb"
) as fh:
    api_single_json = json.load(fh)


def generate_device_with_mocked_hubspace(device_class, **kwargs):
    """Mock the HubSpace connection and force attributes

    During creating, you can specify this information but there may be additional
    things that must be mocked, so go this route to add anything else if required
    """
    with mock.patch(
        "custom_components.hubspace.hubspace.HubSpace", autospec=True
    ) as hs:
        kwargs["hs"] = hs
        if not all(
            [
                kwargs.get("childId"),
                kwargs.get("model"),
                kwargs.get("deviceId"),
                kwargs.get("deviceClass"),
            ]
        ):
            hs.getChildId.return_value = MOCKED_CHILD_DATA
        return device_class(**kwargs)


def validate_hubspace_equals(first, second):
    """Ensure the two HubSpace devices are the same

    This function is required as there is no benefit to add __eq__
    to these classes. Validate all variables minus _hs
    """
    assert isinstance(first, type(second))
    e_vars = vars(first)
    e_vars.pop("_hs")
    exp_vars = vars(second)
    exp_vars.pop("_hs")
    assert e_vars == exp_vars


@pytest.mark.parametrize("ha_entity, expected", [])
def test_create_ha_entity(ha_entity, expected):
    pass


@pytest.mark.parametrize(
    "config,data_path,expected_entities,messages",
    [
        pytest.param(
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                custom_components.hubspace.const.CONF_FRIENDLYNAMES: [],
                custom_components.hubspace.const.CONF_ROOMNAMES: [],
                custom_components.hubspace.const.CONF_DEBUG: True,
            },
            "api_response_single_room.json",
            [
                (
                    light.HubspaceLight,
                    {
                        "_name": "Friendly Name 0",
                        "_childId": "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                        "_model": "TBD",
                        "_deviceId": "80c0c6608a10151f",
                        "_supported_brightness": [x for x in range(1, 101, 1)],
                        "_usePowerFunctionInstance": "light-power",
                    },
                ),
            ],
            [
                # The top-level "ceiling-fan" should not be added
                "Unable to process the entity Friendly Name 1 Fan of class ceiling-fan"
            ],
        ),
    ],
)
def test_setup_platform(
    config, data_path, expected_entities, messages, mocked_hubspace, mocker, caplog
):
    hass = mocker.Mock()
    add_entities = mocker.Mock()
    # Force the class instance creation to use our mocked value
    resp = requests.Response()
    resp.status_code = 200
    with open(os.path.join(current_path, "data", data_path), "rb") as fh:
        resp._content = fh.read()
    resp.encoding = "utf-8"
    mocker.patch.object(light, "HubSpace", return_value=mocked_hubspace)
    mocker.patch.object(mocked_hubspace, "getMetadeviceInfo", return_value=resp)
    light.setup_platform(hass, config, add_entities)
    assert len(add_entities.call_args[0][0]) == len(expected_entities)
    for ind, call in enumerate(add_entities.call_args_list):
        res_entity = call.args[0][0]
        expected_entity_data = expected_entities[ind]
        assert isinstance(res_entity, expected_entity_data[0])
        for key, val in expected_entity_data[1].items():
            assert getattr(res_entity, key) == val
    for message in messages:
        assert message in caplog.text


@pytest.mark.parametrize(
    "values,expected",
    [
        (
            api_single_json[2]["description"]["functions"][1]["values"],
            [2700, 3000, 3500, 4000, 5000, 6500],
        ),
    ],
)
def test_process_color_temps(values, expected):
    assert light.process_color_temps(values) == expected


# @TODO - Add additional tests that support RGB and color-mode
@pytest.mark.parametrize(
    "api_response_file, expected_attrs",
    [
        (
            "light_states.json",
            {
                "_state": "on",
                "_colorTemp": "3500",
                "_brightness": 102,
            },
        ),
    ],
)
def test_HubSpaceLight_update(api_response_file, expected_attrs, mocked_hubspace):
    with open(os.path.join(current_path, "data", api_response_file), "rb") as fh:
        api_response = json.load(fh)
    dev = light.HubspaceLight(mocked_hubspace, "whatever", True)
    dev._hs.get_states.return_value = api_response
    dev.update()
    for key, val in expected_attrs.items():
        assert getattr(dev, key) == val
