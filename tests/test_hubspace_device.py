import json
import os

import pytest

from custom_components.hubspace import hubspace_device

current_path = os.path.dirname(os.path.realpath(__file__))


with open(os.path.join(current_path, "data", "api_response_single_room.json")) as fh:
    api_single = json.load(fh)

with open(os.path.join(current_path, "data", "api_response_multi_room.json")) as fh:
    api_multi = json.load(fh)


@pytest.mark.parametrize(
    "data,room_names,expected",
    [
        # Single room
        (
            api_single,
            ["Doesnt Exist"],
            [],
        ),
        # Single room with three devices
        (
            api_single,
            ["Friendly Name 1"],
            [
                "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                "9916c3fb-e591-4cc0-824a-2e7536f03b1d",
                "f74f69ea-9457-4390-938b-a005d7066ef2",
            ],
        ),
        # Multi-room but single room requested
        (
            api_multi,
            ["Friendly Name 1"],
            [
                "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                "9916c3fb-e591-4cc0-824a-2e7536f03b1d",
            ],
        ),
        # Multi-room with multiple rooms requested
        (
            api_multi,
            ["Friendly Name 1", "Friendly Name 2"],
            [
                "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                "9916c3fb-e591-4cc0-824a-2e7536f03b1d",
                "f74f69ea-9457-4390-938b-a005d7066ef2",
            ],
        ),
    ],
)
def test_get_devices_from_rooms(data, room_names, expected):
    assert hubspace_device.get_devices_from_rooms(data, room_names) == expected


@pytest.mark.parametrize(
    "data,expected",
    [
        (
            [
                {"typeId": "not-a-device", "id": "nope"},
                {"typeId": "metadevice.device", "id": "dev1"},
                {"typeId": "metadevice.device", "id": "dev2"},
            ],
            {
                "dev1": {"typeId": "metadevice.device", "id": "dev1"},
                "dev2": {"typeId": "metadevice.device", "id": "dev2"},
            },
        )
    ],
)
def test_generated_hashed_devices(data, expected):
    assert hubspace_device.generated_hashed_devices(data) == expected


@pytest.mark.parametrize(
    "hs_device,expected",
    [
        # Everything is set correctly
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "model",
                "device_class": "device_class",
                "default_name": "default_name",
                "default_image": "default_image",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "model",
                    "device_class": "device_class",
                    "default_name": "default_name",
                    "default_image": "default_image",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # DriskolFan
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "",
                "device_class": "device_class",
                "default_name": "default_name",
                "default_image": "ceiling-fan-snyder-park-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "DriskolFan",
                    "device_class": "device_class",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-snyder-park-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # VinwoodFan
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "",
                "device_class": "device_class",
                "default_name": "default_name",
                "default_image": "ceiling-fan-vinings-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "VinwoodFan",
                    "device_class": "device_class",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-vinings-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # ZandraFan
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "TBD",
                "device_class": "fan",
                "default_name": "default_name",
                "default_image": "ceiling-fan-chandra-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "ZandraFan",
                    "device_class": "fan",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-chandra-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # NevaliFan
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "TBD",
                "device_class": "fan",
                "default_name": "default_name",
                "default_image": "ceiling-fan-ac-cct-dardanus-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "NevaliFan",
                    "device_class": "fan",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-ac-cct-dardanus-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # TagerFan
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "",
                "device_class": "fan",
                "default_name": "default_name",
                "default_image": "ceiling-fan-slender-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "TagerFan",
                    "device_class": "fan",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-slender-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # Smart Stake Timer
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "Smart Stake Timer",
                "device_class": "fan",
                "default_name": "default_name",
                "default_image": "ceiling-fan-slender-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "YardStake",
                    "device_class": "light",
                    "default_name": "default_name",
                    "default_image": "ceiling-fan-slender-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
        # 12A19060WRGBWH2
        (
            {
                "id": "id",
                "device_id": "device_id",
                "model": "Smart Stake Timer",
                "device_class": "fan",
                "default_name": "default_name",
                "default_image": "a19-e26-color-cct-60w-smd-frosted-icon",
                "friendly_name": "friendly_name",
                "functions": ["functions!"],
            },
            hubspace_device.HubSpaceDevice(
                **{
                    "id": "id",
                    "device_id": "device_id",
                    "model": "12A19060WRGBWH2",
                    "device_class": "light",
                    "default_name": "default_name",
                    "default_image": "a19-e26-color-cct-60w-smd-frosted-icon",
                    "friendly_name": "friendly_name",
                    "functions": ["functions!"],
                }
            ),
        ),
    ],
)
def test_HubSpaceDevice(hs_device, expected):
    assert hubspace_device.HubSpaceDevice(**hs_device) == expected


with open(os.path.join(current_path, "data", "device_lock.json")) as fh:
    device_lock_response = json.load(fh)


@pytest.mark.parametrize(
    "hs_device,expected_attrs",
    [
        # Validate when values are missing
        (
            {},
            {
                "id": None,
                "device_id": None,
                "model": None,
                "device_class": None,
                "default_name": None,
                "default_image": None,
                "friendly_name": None,
                "functions": [],
            },
        ),
        # Ensure values are properly parsed
        (
            device_lock_response[0],
            {
                "id": "5a5d5e04-a6ad-47c0-b9f4-b9fe5c049ef4",
                "device_id": "0123f95ec14bdb23",
                "model": "TBD",
                "device_class": "door-lock",
                "default_name": "Keypad Deadbolt Lock",
                "default_image": "keypad-deadbolt-lock-icon",
                "friendly_name": "Friendly Name 2",
                "functions": device_lock_response[0]["description"]["functions"],
            },
        ),
    ],
)
def test_get_device(hs_device, expected_attrs):
    dev = hubspace_device.get_device(hs_device)
    for key, val in expected_attrs.items():
        assert (
            getattr(dev, key) == val
        ), f"Key {key} did not match, {getattr(dev, key)} != {val}"


with open(os.path.join(current_path, "data", "api_response_multi_room.json")) as fh:
    api_response_multi_room = json.load(fh)


@pytest.mark.parametrize(
    "data, friendly_names, room_names, expected, msgs",
    [
        # Autodiscovery
        (
            device_lock_response,
            [],
            [],
            ["5a5d5e04-a6ad-47c0-b9f4-b9fe5c049ef4"],
            ["Performing auto discovery"],
        ),
        # Manual Discovery - friendlyName exists
        (
            device_lock_response,
            ["Friendly Name 2"],
            [],
            ["5a5d5e04-a6ad-47c0-b9f4-b9fe5c049ef4"],
            ["Performing a manual discovery for friendlyNames"],
        ),
        # Manual Discovery - friendlyName doesn't exist
        (
            device_lock_response,
            ["Friendly Name 1"],
            [],
            [],
            ["Performing a manual discovery for friendlyNames"],
        ),
        # Manual Discovery - friendlyName doesn't exist
        (
            device_lock_response,
            ["Friendly Name 1"],
            ["Room Name 1"],
            [],
            [
                "Performing a manual discovery for friendlyNames",
                "Performing a manual discovery for roomNames",
            ],
        ),
        # Manual Discovery - roomName exists
        (
            api_response_multi_room,
            [],
            ["Friendly Name 1"],
            [
                "9916c3fb-e591-4cc0-824a-2e7536f03b1d",
                "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
            ],
            ["Performing a manual discovery for roomNames"],
        ),
        # Manual Discovery - friendlyName and roomName exists
        (
            api_response_multi_room,
            ["Friendly Name 2"],
            ["Friendly Name 1"],
            [
                "9916c3fb-e591-4cc0-824a-2e7536f03b1d",
                "b1e1213f-9b8e-40c6-96b5-cdee6cf85315",
                "f74f69ea-9457-4390-938b-a005d7066ef2",
            ],
            ["Performing a manual discovery for roomNames"],
        ),
    ],
)
def test_get_requested_ids(data, friendly_names, room_names, expected, msgs, caplog):
    hashed_devices = hubspace_device.generated_hashed_devices(data)
    assert (
        hubspace_device.get_requested_ids(
            data, friendly_names, room_names, hashed_devices
        )
        == expected
    )


@pytest.mark.parametrize(
    "data, friendly_names, room_names, expected, msgs",
    [
        # Autodiscovery
        (
            device_lock_response,
            [],
            [],
            [
                hubspace_device.HubSpaceDevice(
                    **{
                        "id": "5a5d5e04-a6ad-47c0-b9f4-b9fe5c049ef4",
                        "device_id": "0123f95ec14bdb23",
                        "model": "TBD",
                        "device_class": "door-lock",
                        "default_name": "Keypad Deadbolt Lock",
                        "default_image": "keypad-deadbolt-lock-icon",
                        "friendly_name": "Friendly Name 2",
                        "functions": [],
                    }
                )
            ],
            ["Performing auto discovery"],
        ),
        # Manual Discovery - friendlyName exists
        (
            device_lock_response,
            ["Friendly Name 2"],
            [],
            [
                hubspace_device.HubSpaceDevice(
                    **{
                        "id": "5a5d5e04-a6ad-47c0-b9f4-b9fe5c049ef4",
                        "device_id": "0123f95ec14bdb23",
                        "model": "TBD",
                        "device_class": "door-lock",
                        "default_name": "Keypad Deadbolt Lock",
                        "default_image": "keypad-deadbolt-lock-icon",
                        "friendly_name": "Friendly Name 2",
                        "functions": [],
                    }
                )
            ],
            ["Performing a manual discovery for friendlyNames"],
        ),
    ],
)
def test_get_hubspace_devices(data, friendly_names, room_names, expected, msgs, caplog):
    devices = [
        x
        for x in hubspace_device.get_hubspace_devices(data, friendly_names, room_names)
    ]
    assert len(devices) == len(expected)
    for ind, device in enumerate(devices):
        # We know functions correctly work from test_get_device so skip that one
        attrs_to_validate = [
            "id",
            "device_id",
            "model",
            "device_class",
            "default_name",
            "default_image",
            "friendly_name",
        ]
        for attr in attrs_to_validate:
            assert getattr(device, attr) == getattr(expected[ind], attr)
    for message in msgs:
        assert message in caplog.text
