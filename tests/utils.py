"""Assists in executing tests by making it easy to load data dumps."""

import json
import os
from pathlib import Path
from typing import Any

from aioafero import AferoDevice, AferoState

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
        if "children" not in device:
            device["children"] = []
        processed.append(AferoDevice(**device))
    return processed


def hs_raw_from_dump(file_name: str) -> list[dict]:
    """Generate a Hubspace payload from devices and save it to a file.

    Takes a device dump file and process into a "raw" Afero format. This
    enables one dump for testing raw and processed sides.

    :param file_name: Name of the file that contains the dump
    :return: List of dictionaries containing the generated Hubspace payload
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
    return hs_raw


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
