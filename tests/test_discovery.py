import logging
from asyncio import Future

import pytest
from hubspace_async import HubSpaceDevice, HubSpaceRoom

from custom_components.hubspace import discovery


def generate_hs_device(friendly_id: str, child_id: str, **kwargs) -> HubSpaceDevice:
    dev_dict = {
        "id": child_id,
        "device_id": "parent-id",
        "model": "model",
        "device_class": "device-class",
        "default_name": "default-name",
        "default_image": "default-image",
        "friendly_name": friendly_id,
        "functions": [],
    }
    dev_dict.update(kwargs)
    return HubSpaceDevice(**dev_dict)


TEST_DEV_1 = generate_hs_device("friendly-1", "id-1")
TEST_DEV_2 = generate_hs_device("friendly-2", "id-2")
TEST_DEV_3 = generate_hs_device("friendly-3", "id-3")
TEST_DEV_4 = generate_hs_device("friendly-4", "id-4")
TEST_DEVS = {
    TEST_DEV_1.id: TEST_DEV_1,
    TEST_DEV_2.id: TEST_DEV_2,
    TEST_DEV_3.id: TEST_DEV_3,
    TEST_DEV_4.id: TEST_DEV_4,
}

TEST_ROOM_1 = HubSpaceRoom(friendly_name="room-1", id="id-1", children=[])
TEST_ROOM_2 = HubSpaceRoom(
    friendly_name="room-2", id="id-2", children=[TEST_DEV_1, TEST_DEV_2]
)
TEST_ROOM_3 = HubSpaceRoom(friendly_name="room-2", id="id-3", children=[TEST_DEV_3])
TEST_ROOMS = {
    TEST_ROOM_1.id: TEST_ROOM_1,
    TEST_ROOM_2.id: TEST_ROOM_2,
    TEST_ROOM_3.id: TEST_ROOM_3,
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "devices,friendly_names,expected_devices",
    [
        # Empty
        ({}, [], []),
        # No matches
        (TEST_DEVS, ["i-dont-exist"], []),
        # Match a single device
        (TEST_DEVS, [TEST_DEV_1.friendly_name], [TEST_DEV_1]),
        # Match multiple device
        (
            TEST_DEVS,
            [TEST_DEV_1.friendly_name, TEST_DEV_2.friendly_name],
            [TEST_DEV_1, TEST_DEV_2],
        ),
    ],
)
async def test_get_devices_from_friendly_names(
    devices, friendly_names, expected_devices, mocked_hubspace
):
    dev_response = Future()
    dev_response.set_result(devices)
    mocked_hubspace.devices = dev_response
    assert (
        await discovery.get_devices_from_friendly_names(mocked_hubspace, friendly_names)
        == expected_devices
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rooms,friendly_names,expected_devices",
    [
        # Empty
        ({}, [], []),
        # No matches
        (TEST_ROOMS, ["i-dont-exist"], []),
        # Match a single room
        (TEST_ROOMS, [TEST_ROOM_2.friendly_name], [TEST_DEV_1, TEST_DEV_2, TEST_DEV_3]),
        # Match multiple rooms
        (
            TEST_ROOMS,
            [TEST_ROOM_2.friendly_name, TEST_ROOM_3.friendly_name],
            [TEST_DEV_1, TEST_DEV_2, TEST_DEV_3],
        ),
    ],
)
async def test_get_devices_from_rooms(
    rooms, friendly_names, expected_devices, mocked_hubspace
):
    room_response = Future()
    room_response.set_result(rooms)
    mocked_hubspace.rooms = room_response
    assert (
        await discovery.get_devices_from_rooms(mocked_hubspace, friendly_names)
        == expected_devices
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rooms, devices, dev_names, room_names, expected, messages",
    [
        # Match on friendly names
        (
            TEST_ROOMS,
            TEST_DEVS,
            [TEST_DEV_1.friendly_name, TEST_DEV_2.friendly_name],
            [],
            [TEST_DEV_1, TEST_DEV_2],
            ["Performing a manual discovery for friendlyNames"],
        ),
        # Duplicate friendly
        (
            TEST_ROOMS,
            TEST_DEVS,
            [TEST_DEV_1.friendly_name, TEST_DEV_1.friendly_name],
            [],
            [TEST_DEV_1],
            ["Performing a manual discovery for friendlyNames"],
        ),
        # Match on rooms
        (
            TEST_ROOMS,
            TEST_DEVS,
            [],
            [TEST_ROOM_2.friendly_name, TEST_ROOM_3.friendly_name],
            [TEST_DEV_1, TEST_DEV_2, TEST_DEV_3],
            ["Performing a manual discovery for roomNames"],
        ),
        # Match on both
        (
            TEST_ROOMS,
            TEST_DEVS,
            [TEST_DEV_3.friendly_name],
            [TEST_ROOM_2.friendly_name],
            [TEST_DEV_1, TEST_DEV_2, TEST_DEV_3],
            [
                "Performing a manual discovery for friendlyNames",
                "Performing a manual discovery for roomNames",
            ],
        ),
        # Auto-discovery
        (
            TEST_ROOMS,
            TEST_DEVS,
            [],
            [],
            [TEST_DEV_1, TEST_DEV_2, TEST_DEV_3, TEST_DEV_4],
            ["Performing auto discovery"],
        ),
    ],
)
async def test_get_requested_devices(
    rooms, devices, dev_names, room_names, expected, messages, mocked_hubspace, caplog
):
    caplog.set_level(logging.DEBUG)
    dev_response = Future()
    dev_response.set_result(devices)
    mocked_hubspace.devices = dev_response
    room_response = Future()
    room_response.set_result(rooms)
    mocked_hubspace.rooms = room_response
    assert (
        await discovery.get_requested_devices(mocked_hubspace, dev_names, room_names)
        == expected
    )
    for message in messages:
        assert message in caplog.text
