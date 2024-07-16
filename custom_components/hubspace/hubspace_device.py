__all__ = ["HubSpaceDevice", "get_hubspace_devices", "get_devices_cached", "get_device_cached"]
from typing import Any, Generator
from dataclasses import dataclass
import logging
from .hubspace import HubSpace


logger = logging.getLogger(__name__)
from cachetools import TTLCache, cached


@dataclass
class HubSpaceDevice:
    id: str
    device_id: str
    model: str
    device_class: str
    default_name: str
    default_image: str
    friendly_name: str
    functions: list[dict]


    def __post_init__(self):
        if not self.model and self.default_image == "ceiling-fan-snyder-park-icon":
            self.model = "DriskolFan"
        if not self.model and self.default_image == "ceiling-fan-vinings-icon":
            self.model = "VinwoodFan"
        if self.device_class == "fan" and self.model == "TBD" and self.default_image == "ceiling-fan-chandra-icon":
            self.model = "ZandraFan"
        if self.model == "TBD" and self.default_image == "ceiling-fan-ac-cct-dardanus-icon":
            self.model = "NevaliFan"
        if self.device_class == "fan" and not self.model and self.default_image == "ceiling-fan-slender-icon":
            self.model = "TagerFan"
        if self.model == "Smart Stake Timer":
            self.model = "YardStake"
            self.device_class = "light"
        if self.default_image == "a19-e26-color-cct-60w-smd-frosted-icon":
            self.model = "12A19060WRGBWH2"


def get_devices_from_rooms(data: list[dict], room_names: list[str]) -> list[str]:
    """Find all devices related to a room

    :param data: API response for the account
    :param room_names: List of room names

    :return: List of Device IDs related to the room
    """
    devices: list[str] = []
    for element in data:
        if element.get("typeId") != "metadevice.room":
            continue
        if element.get("friendlyName") not in room_names:
            continue
        devices.extend(element["children"])
    return devices


def get_devices_from_friendly_names(data: list[dict], friendly_names: list[str]) -> list[str]:
    """Find all devices related to a room

    :param data: API response for the account
    :param friendly_names: List of devices to filter

    :return: List of Device IDs related to the friendly names
    """
    devices: list[str] = []
    for element in data:
        if element.get("typeId") != "metadevice.device":
            continue
        if element.get("friendlyName") not in friendly_names:
            continue
        if element.get("children"):
            continue
        devices.append(element.get("id"))
    return devices


def generated_hashed_devices(data: list) -> dict[str, Any]:
    """Convert the response list to a dictionary indexed by id

    :param data: API response for the account
    """
    devices: dict[str, Any] = {}
    for device in data:
        if device.get("typeId") not in ["metadevice.device"]:
            continue
        devices[device["id"]] = device
    return devices


def get_device(hs_device: dict[str, Any]) -> HubSpaceDevice:
    """Convert the HubSpace device definition into a HubSpaceDevice"""
    description = hs_device.get("description", {})
    device = description.get("device", {})
    dev_dict = {
        "id": hs_device.get("id"),
        "device_id": hs_device.get("deviceId"),
        "model": device.get("model"),
        "device_class": device.get("deviceClass"),
        "default_name": device.get("defaultName"),
        "default_image": description.get("defaultImage"),
        "friendly_name": hs_device.get("friendlyName"),
        "functions": description.get("functions", []),
    }
    return HubSpaceDevice(**dev_dict)


def get_requested_ids(data: list[dict], friendly_names: list[str], room_names: list[str], hashed_devices: dict) -> list[str]:
    """Find all devices that need to be discovered

    :param data: API response for the account
    :param friendly_names: List of devices to filter
    :param room_names: List of room names
    :param hashed_devices: Devices indexed by their ID
    """
    device_ids = set()
    if friendly_names:
        logger.debug("Performing a manual discovery for friendlyNames")
        device_ids.update(set(get_devices_from_friendly_names(data, friendly_names)))
    if room_names:
        logger.debug("Performing a manual discovery for roomNames")
        device_ids.update(set(get_devices_from_rooms(data, room_names)))
    if not (friendly_names or room_names):
        logger.debug("Performing auto discovery")
        device_ids = set(hashed_devices.keys())
    return sorted(list(device_ids))


def get_hubspace_devices(data: list[dict], friendly_names: list[str], room_names: list[str]) -> Generator:
    """Generate a HubSpaceDevice for each requested devices
    """
    hashed_devices = generated_hashed_devices(data)
    device_ids = get_requested_ids(data, friendly_names, room_names, hashed_devices)
    for device_id in device_ids:
        yield get_device(hashed_devices[device_id])


@cached(cache=TTLCache(maxsize=1, ttl=5))
def get_devices_cached(hs: HubSpace) -> dict[str, Any]:
    """Get all devices from cache

    Cache is stored for 5s as it can be used for multiple entities

    :param hs: HubSpace connection
    """
    data = hs.getMetadeviceInfo().json()
    return generated_hashed_devices(data)


def get_device_cached(hs: HubSpace, child_id: str) -> HubSpaceDevice:
    """Lookup a device from the device list

    :param hs: HubSpace connection
    :param child_id: Child Device ID to lookup
    """
    devices = get_devices_cached(hs)
    return get_device(devices[child_id])
