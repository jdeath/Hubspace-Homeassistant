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
