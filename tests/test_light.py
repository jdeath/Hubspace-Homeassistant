import json
import os
from unittest import mock
import requests

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

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


with open(os.path.join(current_path, "data", "api_response_single_room.json"), "rb") as fh:
    api_single = fh.read()


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


@pytest.mark.parametrize(
    "ha_entity, expected", [

    ]
)
def test_create_ha_entity(ha_entity, expected):
    pass


@pytest.mark.parametrize(
    "config,data,expected_entities,messages",
    [
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            None,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight,
                    friendlyname="Friendly Name 0",
                    debug=True,
                    childId="b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                    model="TBD",
                    deviceId="80c0c6608a10151f",
                    deviceClass="DoesntMatter",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceFan,
                    friendlyname="Friendly Name 2",
                    debug=True,
                    childId="e60c2391-ca03-49fa-b872-7ad5bb1e2815",
                    model="ZandraFan",
                    deviceId="80c0c6608a10151f",
                    deviceClass="fan",
                ),
            ],
            [
                # The top-level "ceiling-fan" should not be added
                "Unable to process the entity Friendly Name 1 Fan of class ceiling-fan"
            ]
        ),
    ]
)
def test_setup_platform(
    config, data, expected_entities, messages, mocked_hubspace, mocker, caplog
):
    hass = mocker.Mock()
    add_entities = mocker.Mock()
    # Force the class instance creation to use our mocked value
    resp = requests.Response()
    resp.status_code = 200
    resp._content = api_single
    resp.encoding = "utf-8"
    mocker.patch.object(light, "HubSpace", return_value=mocked_hubspace)
    mocker.patch.object(mocked_hubspace, "getMetadeviceInfo", return_value=resp)
    light.setup_platform(hass, config, add_entities)
    assert len(add_entities.call_args[0][0]) == len(expected_entities)
    for ind, call in enumerate(add_entities.call_args_list):
        validate_hubspace_equals(call.args[0][0], expected_entities[ind])
    for message in messages:
        assert message in caplog.text
