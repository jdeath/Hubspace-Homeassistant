__all__ = ["get_requested_devices"]
import logging

from hubspace_async import HubSpaceConnection, HubSpaceDevice

logger = logging.getLogger(__name__)


async def get_devices_from_friendly_names(
    conn: HubSpaceConnection, friendly_names: list[str]
) -> list[HubSpaceDevice]:
    """Find all devices related to a room

    :param conn: Connection to the HubSpace API
    :param friendly_names: List of devices to filter

    :return: List of HubSpace devices that match the friendly names
    """
    devices: list[HubSpaceDevice] = []
    for device in (await conn.devices).values():
        if device.friendly_name not in friendly_names:
            continue
        devices.append(device)
    return devices


async def get_devices_from_rooms(
    conn: HubSpaceConnection, room_names: list[str]
) -> list[HubSpaceDevice]:
    """Find all devices related to a room

    :param conn: Connection to the HubSpace API
    :param room_names: List of rooms to gather devices

    :return: List of HubSpace devices that match the room names
    """
    devices: list[HubSpaceDevice] = []
    for room in (await conn.rooms).values():
        if room.friendly_name not in room_names:
            continue
        devices.extend(room.children)
    return devices


async def get_requested_devices(
    conn: HubSpaceConnection,
    friendly_names: list[str],
    room_names: list[str],
) -> list[HubSpaceDevice]:
    """Find all devices that need to be discovered

    :param conn: Connection to the HubSpace API
    :param friendly_names: List of devices to filter
    :param room_names: List of room names
    """
    devices: set[HubSpaceDevice] = set()
    if friendly_names:
        logger.debug("Performing a manual discovery for friendlyNames")
        devices.update(await get_devices_from_friendly_names(conn, friendly_names))
    if room_names:
        logger.debug("Performing a manual discovery for roomNames")
        devices.update(set(await get_devices_from_rooms(conn, room_names)))
    if not (friendly_names or room_names):
        logger.debug("Performing auto discovery")
        devices = set((await conn.devices).values())
    sorted_devs = sorted(list(devices), key=lambda dev: dev.friendly_name)
    dev_names = ", ".join([x.friendly_name for x in sorted_devs])
    logger.info("Performing discovery for the following friendly names: %s", dev_names)
    return sorted_devs
