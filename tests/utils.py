import json
import os
from typing import Any

from aiohubspace import HubspaceDevice, HubspaceState

current_path: str = os.path.dirname(os.path.realpath(__file__))


def get_device_dump(file_name: str) -> Any:
    """Get a device dump

    :param file_name: Name of the file to load
    """
    with open(os.path.join(current_path, "device_dumps", file_name), "r") as fh:
        return json.load(fh)


def create_devices_from_data(file_name: str) -> list[HubspaceDevice]:
    """Generate devices from a data dump

    :param file_name: Name of the file to load
    """
    devices = get_device_dump(file_name)
    processed: list[HubspaceDevice] = []
    for device in devices:
        processed_states = []
        for state in device["states"]:
            processed_states.append(HubspaceState(**state))
        device["states"] = processed_states
        if "children" not in device:
            device["children"] = []
        processed.append(HubspaceDevice(**device))
    return processed


def create_hs_raw_from_dump(file_name: str) -> list[dict]:
    """Generate a Hubspace payload from devices

    :param file_name: Name of the file that contains the dump
    """
    hs_raw: list[dict] = []
    for device in create_devices_from_data(file_name):
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
        hs_raw.append(
            {
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
                "typeId": "metadevice.device",
            }
        )
    filename = os.path.basename(file_name).rsplit(".", 1)[0]
    new_filename = f"{filename}-raw.json"
    with open(new_filename, "w") as fh:
        fh.write(json.dumps(hs_raw, indent=4))

    return hs_raw


def convert_states(states: list[HubspaceState]) -> list[dict]:
    """Converts states from HubspaceState to raw

    :param states: List of HubspaceState objects
    """
    raw_states = []
    for state in states:
        raw_states.append(
            {
                "functionClass": state.functionClass,
                "functionInstance": state.functionInstance,
                "lastUpdateTime": state.lastUpdateTime,
                "value": state.value,
            }
        )
    return raw_states


def modify_state(device: HubspaceDevice, new_state):
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
