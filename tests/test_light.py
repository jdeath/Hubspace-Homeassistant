import json
import os
from unittest import mock

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


def mock_ex1_getChildId(friendly_name):
    """Mock for setup_platform for getChildID"""
    # [childId, model, deviceId, deviceClass]
    return MOCKED_TEST_DATA.get(friendly_name)


@pytest.mark.parametrize(
    "entities,model,device_class,friendly_name,expected",
    [
        # Outlet - 2 port
        (
            [],
            "HPKA315CWB",
            "Doesnt Matter",
            "Outlet - 2 Port",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 2 Port",
                    outletIndex="1",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 2 Port",
                    outletIndex="2",
                    debug=True,
                ),
            ],
        ),
        # Outlet - 4 port
        (
            [],
            "LTS-4G-W",
            "Doesnt Matter",
            "Outlet - 4 Port",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 4 Port",
                    outletIndex="1",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 4 Port",
                    outletIndex="2",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 4 Port",
                    outletIndex="3",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="Outlet - 4 Port",
                    outletIndex="4",
                    debug=True,
                ),
            ],
        ),
        # Transformer
        (
            [],
            "HB-200-1215WIFIB",
            "Doesnt Matter",
            "Transformer",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceTransformer,
                    friendlyname="Transformer",
                    outletIndex="1",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceTransformer,
                    friendlyname="Transformer",
                    outletIndex="2",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceTransformer,
                    friendlyname="Transformer",
                    outletIndex="3",
                    debug=True,
                ),
            ],
        ),
        # Fan
        (
            [],
            "52133, 37833",
            "Doesnt Matter",
            "Fan with Light",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceFan, friendlyname="Fan with Light", debug=True
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="Fan with Light", debug=True
                ),
            ],
        ),
        # Fan
        (
            [],
            "76278, 37278",
            "Doesnt Matter",
            "Fan with Light",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceFan, friendlyname="Fan with Light", debug=True
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="Fan with Light", debug=True
                ),
            ],
        ),
        # Fan
        (
            [],
            "ZandraFan",
            "Doesnt Matter",
            "Fan with Light",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceFan, friendlyname="Fan with Light", debug=True
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="Fan with Light", debug=True
                ),
            ],
        ),
        # Door Lock
        (
            [],
            "TBD",
            "door-lock",
            "Door Lock",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLock, friendlyname="Door Lock", debug=True
                ),
            ],
        ),
        # Water Timer
        (
            [],
            "Doesnt Matter",
            "water-timer",
            "Water Timer",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceWaterTimer,
                    friendlyname="Water Timer",
                    outletIndex="1",
                    debug=True,
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceWaterTimer,
                    friendlyname="Water Timer",
                    outletIndex="2",
                    debug=True,
                ),
            ],
        ),
        # Anything else just becomes a light
        (
            [],
            "Doesnt Matter",
            "Doesnt Matter",
            "im-a-light",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="im-a-light", debug=True
                ),
            ],
        ),
        # Add a light when entities already exist
        # Anything else just becomes a light
        (
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="im-a-light1", debug=True
                ),
            ],
            "Doesnt Matter",
            "Doesnt Matter",
            "im-a-light2",
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="im-a-light1", debug=True
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight, friendlyname="im-a-light2", debug=True
                ),
            ],
        ),
    ],
)
# entities: list, hs: HubSpace, model: str, deviceClass: str, friendlyName: str, debug: bool
def test__add_entity(
    entities, model, device_class, friendly_name, expected, mocked_hubspace
):
    mocked_hubspace.getChildId.return_value = MOCKED_CHILD_DATA
    light._add_entity(
        entities, mocked_hubspace, model, device_class, friendly_name, True
    )
    assert len(entities) == len(expected)
    for ind, entity in enumerate(entities):
        validate_hubspace_equals(entity, expected[ind])


@pytest.mark.parametrize(
    "config,getChildID,expected_entities",
    [
        # Single Device
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: ["test-light-1"],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            mock_ex1_getChildId,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight,
                    friendlyname="test-light-1",
                    debug=True,
                    childId="childId1",
                    model="HPPA51CWB",
                    deviceId="some-cool-light",
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
        # Multiple Devices
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: ["test-light-1", "test-outlet-1"],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            mock_ex1_getChildId,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight,
                    friendlyname="test-light-1",
                    debug=True,
                    childId="childId1",
                    model="HPPA51CWB",
                    deviceId="some-cool-light",
                    deviceClass="DoesntMatter",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="test-outlet-1",
                    debug=True,
                    childId="childId2",
                    model="HPPA51CWB",
                    deviceId="some-cool-switch",
                    deviceClass="DoesntMatter",
                    outletIndex="1",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="test-outlet-1",
                    debug=True,
                    childId="childId2",
                    model="HPPA51CWB",
                    deviceId="some-cool-switch",
                    deviceClass="DoesntMatter",
                    outletIndex="2",
                ),
            ],
        ),
    ],
)
def test_setup_platform_manual(
    config, getChildID, expected_entities, mocked_hubspace, mocker
):
    hass = mocker.Mock()
    add_entities = mocker.Mock()
    # Force the call to return our test data
    mocker.patch.object(mocked_hubspace, "getChildId", side_effect=getChildID)
    # Force the class instance creation to use our mocked value
    mocker.patch.object(light, "HubSpace", return_value=mocked_hubspace)
    light.setup_platform(hass, config, add_entities)
    assert len(add_entities.call_args[0][0]) == len(expected_entities)
    for ind, call in enumerate(add_entities.call_args_list):
        validate_hubspace_equals(call.args[0][0], expected_entities[ind])


def autodiscovery_light(*args, **kwargs):
    yield (
        MOCKED_TEST_DATA["test-light-1"][0],
        MOCKED_TEST_DATA["test-light-1"][1],
        MOCKED_TEST_DATA["test-light-1"][2],
        MOCKED_TEST_DATA["test-light-1"][3],
        "test-light-1",
        [],
    )


def autodiscovery_driskolfan(*args, **kwargs):
    yield (
        MOCKED_TEST_DATA["test-fan-driskol"][0],
        MOCKED_TEST_DATA["test-fan-driskol"][1],
        MOCKED_TEST_DATA["test-fan-driskol"][2],
        MOCKED_TEST_DATA["test-fan-driskol"][3],
        "test-fan-driskol",
        [],
    )


current_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(current_path, "data", "outlet.json")) as fh:
    outlet_data = json.load(fh)


def autodiscovery_outlet(*args, **kwargs):
    yield (
        MOCKED_TEST_DATA["test-outlet-1"][0],
        MOCKED_TEST_DATA["test-outlet-1"][1],
        MOCKED_TEST_DATA["test-outlet-1"][2],
        MOCKED_TEST_DATA["test-outlet-1"][3],
        "test-outlet-1",
        outlet_data,
    )


# Using outlet_data may be incorrect but I dont see any data on this and
# the code is similar
def autodiscovery_transformer(*args, **kwargs):
    yield (
        MOCKED_TEST_DATA["test-transformer-1"][0],
        MOCKED_TEST_DATA["test-transformer-1"][1],
        MOCKED_TEST_DATA["test-transformer-1"][2],
        MOCKED_TEST_DATA["test-transformer-1"][3],
        "test-transformer-1",
        outlet_data,
    )


# Using outlet_data may be incorrect but I dont see any data on this and
# the code is similar
def autodiscovery_water_timer(*args, **kwargs):
    yield (
        MOCKED_TEST_DATA["test-water-1"][0],
        MOCKED_TEST_DATA["test-water-1"][1],
        MOCKED_TEST_DATA["test-water-1"][2],
        MOCKED_TEST_DATA["test-water-1"][3],
        "test-water-1",
        outlet_data,
    )


@pytest.mark.parametrize(
    "config, device_ids_generator, expected_entities",
    [
        # Driskol Fan
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            autodiscovery_driskolfan,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceFan,
                    friendlyname="test-fan-driskol",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-fan-driskol"][0],
                    model="DriskolFan",
                    deviceId=MOCKED_TEST_DATA["test-fan-driskol"][2],
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
        # Light
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            autodiscovery_light,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceLight,
                    friendlyname="test-light-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-light-1"][0],
                    model=MOCKED_TEST_DATA["test-light-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-light-1"][2],
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
        # Power Outlet
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            autodiscovery_outlet,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="test-outlet-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-outlet-1"][0],
                    model=MOCKED_TEST_DATA["test-outlet-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-outlet-1"][2],
                    outletIndex="2",
                    deviceClass="DoesntMatter",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceOutlet,
                    friendlyname="test-outlet-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-outlet-1"][0],
                    model=MOCKED_TEST_DATA["test-outlet-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-outlet-1"][2],
                    outletIndex="1",
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
        # Transformer
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            autodiscovery_transformer,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceTransformer,
                    friendlyname="test-transformer-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-transformer-1"][0],
                    model=MOCKED_TEST_DATA["test-transformer-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-transformer-1"][2],
                    outletIndex="2",
                    deviceClass="DoesntMatter",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceTransformer,
                    friendlyname="test-transformer-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-transformer-1"][0],
                    model=MOCKED_TEST_DATA["test-transformer-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-transformer-1"][2],
                    outletIndex="1",
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
        # Transformer
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                light.CONF_FRIENDLYNAMES: [],
                light.CONF_ROOMNAMES: [],
                light.CONF_DEBUG: True,
            },
            autodiscovery_water_timer,
            [
                generate_device_with_mocked_hubspace(
                    light.HubspaceWaterTimer,
                    friendlyname="test-water-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-water-1"][0],
                    model=MOCKED_TEST_DATA["test-water-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-water-1"][2],
                    outletIndex="2",
                    deviceClass="DoesntMatter",
                ),
                generate_device_with_mocked_hubspace(
                    light.HubspaceWaterTimer,
                    friendlyname="test-water-1",
                    debug=True,
                    childId=MOCKED_TEST_DATA["test-water-1"][0],
                    model=MOCKED_TEST_DATA["test-water-1"][1],
                    deviceId=MOCKED_TEST_DATA["test-water-1"][2],
                    outletIndex="1",
                    deviceClass="DoesntMatter",
                ),
            ],
        ),
    ],
)
def test_setup_platform_auto(
    config, device_ids_generator, expected_entities, mocked_hubspace, mocker
):
    hass = mocker.Mock()
    add_entities = mocker.Mock()
    # Force the call to return our test data
    mocker.patch.object(
        mocked_hubspace, "discoverDeviceIds", side_effect=device_ids_generator
    )
    # Force the class instance creation to use our mocked value
    mocker.patch.object(light, "HubSpace", return_value=mocked_hubspace)
    light.setup_platform(hass, config, add_entities)
    assert len(add_entities.call_args[0][0]) == len(expected_entities)
    for ind, call in enumerate(add_entities.call_args_list):
        validate_hubspace_equals(call.args[0][0], expected_entities[ind])
