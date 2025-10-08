"""Assists in executing tests by making it easy to load data dumps."""

import asyncio
import datetime
import json
import os
from pathlib import Path
from typing import Any

from aioafero import AferoCapability, AferoDevice, AferoState, v1
from aioafero.v1.auth import TokenData
from aioafero.v1.controllers.base import dataclass_to_afero
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace.const import (
    CONF_CLIENT,
    DEFAULT_CLIENT,
    DEFAULT_POLLING_INTERVAL_SEC,
    DOMAIN,
    POLLING_TIME_STR,
    VERSION_MAJOR,
    VERSION_MINOR,
)

current_path: Path = Path(__file__.rsplit(os.sep, 1)[0])


def get_device_dump(file_name: Path) -> Any:
    """Load and parse a JSON device dump file.

    Takes a filename and loads the corresponding JSON device dump file from the
    device_dumps directory. The file should contain serialized device data.

    :param file_name: Name of the file to load from device_dumps directory
    :return: Parsed JSON data containing device information
    """
    with Path(current_path / "device_dumps" / file_name).open() as fh:
        return json.load(fh)


def create_devices_from_data(file_name: str) -> list[AferoDevice]:
    """Generate a list of AferoDevice objects from a data dump file.

    Loads device data from a JSON dump file, processes the states into AferoState
    objects, ensures children field exists, and creates AferoDevice instances.

    :param file_name: Name of the file to load
    :return: List of processed AferoDevice objects
    """
    path_obj = Path(file_name)
    devices = get_device_dump(path_obj)
    processed: list[AferoDevice] = []
    for device in devices:
        processed_states = [AferoState(**state) for state in device["states"]]
        device["states"] = processed_states
        device["capabilities"] = [
            AferoCapability(**cap) for cap in device.get("capabilities", [])
        ]
        if "children" not in device:
            device["children"] = []
        processed.append(AferoDevice(**device))
    return processed


def hs_raw_from_dump(file_name: str) -> list[dict]:
    """Generate a Hubspace payload from devices.

    Takes a device dump file and process into a "raw" Afero format. This
    enables one dump for testing raw and processed sides.

    :param file_name: Name of the file that contains the dump
    :return: List of dictionaries containing the generated Hubspace payload
    """
    return [
        hs_raw_from_device(device) for device in create_devices_from_data(file_name)
    ]


def hs_raw_from_device(device: AferoDevice) -> dict:
    """Generate a Hubspace payload from an AferoDevice.

    :param device: Device to convert to a raw dump
    """
    descr_device = {
        "defaultName": device.default_name,
        "deviceClass": device.device_class,
        "manufacturerName": device.manufacturerName,
        "model": device.model,
        "profileId": "6ea6d241-3909-4235-836d-c594ece2bb67",
        "type": "device",
    }
    description = {
        "createdTimestampMs": 0,
        "defaultImage": device.default_image,
        "descriptions": [],
        "device": descr_device,
        "functions": device.functions,
        "hints": [],
        "id": device.id,
        "updatedTimestampMs": 0,
        "version": 1,
    }
    return {
        "children": device.children,
        "createdTimestampMs": 0,
        "description": description,
        "deviceId": device.device_id,
        "friendlyDescription": "",
        "friendlyName": device.friendly_name,
        "id": device.id,
        "state": {
            "metadeviceId": device.id,
            "values": convert_states(device.states),
        },
        "capabilities": [x.raw_dump() for x in device.capabilities],
        "typeId": "metadevice.device",
        "version_data": device.version_data,
    }


def create_hs_raw_from_dump(file_name: str) -> list[dict]:
    """Generate a Hubspace payload from devices and save it to a file.

    Takes a device dump file, processes it into Hubspace format, and saves the
    result to a new JSON file with '-raw' suffix. The generated payload includes
    device details, descriptions, states and other metadata formatted for Hubspace.

    :param file_name: Name of the file that contains the dump
    :return: List of dictionaries containing the generated Hubspace payload
    """
    hs_raw = hs_raw_from_dump(file_name)
    filename = Path(file_name).name.rsplit(".", 1)[0]
    new_filename = f"{filename}-raw.json"
    with Path(new_filename).open("w") as fh:
        fh.write(json.dumps(hs_raw, indent=4))

    return hs_raw


def convert_states(states: list[AferoState]) -> list[dict]:
    """Convert the states from AferoState to raw.

    :param states: List of AferoState objects
    """
    return [
        {
            "functionClass": state.functionClass,
            "functionInstance": state.functionInstance,
            "lastUpdateTime": state.lastUpdateTime,
            "value": state.value,
        }
        for state in states
    ]


def modify_state(device: AferoDevice, new_state: AferoState):
    """Adjust a state for the given device.

    @param device: AferoDevice to modify
    @param new_state: Replacement state
    """
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


def get_mocked_bridge(mocker) -> v1.AferoBridgeV1:
    """Create a mocked afero bridge to be used in tests."""
    mocker.patch("aioafero.v1.controllers.event.EventStream.gather_data")

    bridge: v1.AferoBridgeV1 = v1.AferoBridgeV1("username2", "password2")
    mocker.patch.object(bridge, "_account_id", "mocked-account-id")
    mocker.patch.object(bridge, "fetch_data", return_value=[])
    mocker.patch.object(bridge, "request", side_effect=mocker.AsyncMock())
    mocker.patch.object(bridge.events, "_first_poll_completed", True)
    mocker.patch.object(
        bridge, "fetch_data", side_effect=mocker.AsyncMock(return_value=[])
    )

    bridge.set_token_data(
        TokenData(
            "mock-token",
            "mock-access",
            "mock-refresh-token",
            expiration=datetime.datetime.now().timestamp() + 200,
        )
    )

    # Enable ad-hoc polls
    async def generate_events_from_data(data):
        task = asyncio.create_task(bridge.events.generate_events_from_data(data))
        await task
        raw_data = await bridge.events.generate_events_from_data(data)
        mocker.patch(
            "aioafero.v1.controllers.event.EventStream.gather_data",
            return_value=raw_data,
        )
        await bridge.async_block_until_done()

    # Fake a poll for discovery
    async def generate_devices_from_data(devices: list[AferoDevice]):
        raw_data = [hs_raw_from_device(device) for device in devices]
        mocker.patch(
            "aioafero.v1.controllers.event.EventStream.gather_data",
            return_value=raw_data,
        )
        await bridge.events.generate_events_from_data(raw_data)
        await bridge.async_block_until_done()

    # Fake the response from the API when updating states
    def mock_update_afero_api(device_id, result):
        json_resp = mocker.AsyncMock()
        json_resp.return_value = {"metadeviceId": device_id, "values": result}
        resp = mocker.AsyncMock()
        resp.json = json_resp
        resp.status = 200
        mocker.patch(
            "aioafero.v1.controllers.base.BaseResourcesController.update_afero_api",
            return_value=resp,
        )

    # Enable "results" to be returned on update
    actual_dataclass_to_afero = dataclass_to_afero

    def mocked_dataclass_to_afero(*args, **kwargs):
        result = actual_dataclass_to_afero(*args, **kwargs)
        mock_update_afero_api(args[0].id, result)
        return result

    mocker.patch(
        "aioafero.v1.controllers.base.dataclass_to_afero",
        side_effect=mocked_dataclass_to_afero,
    )

    bridge.mock_update_afero_api = mock_update_afero_api
    bridge.generate_devices_from_data = generate_devices_from_data
    bridge.generate_events_from_data = generate_events_from_data

    return bridge


def get_mocked_entry(hass, mocker, mocked_bridge) -> MockConfigEntry:
    """Register plugin with a config entry."""
    # Prepare the entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "username",
            CONF_PASSWORD: "password",
            CONF_TOKEN: "mock-token",
            CONF_CLIENT: DEFAULT_CLIENT,
        },
        options={
            CONF_TIMEOUT: 30,
            POLLING_TIME_STR: DEFAULT_POLLING_INTERVAL_SEC,
        },
        version=VERSION_MAJOR,
        minor_version=VERSION_MINOR,
    )
    entry.add_to_hass(hass)
    mocker.patch(
        "custom_components.hubspace.bridge.AferoBridgeV1", return_value=mocked_bridge
    )
    return hass, entry, mocked_bridge
