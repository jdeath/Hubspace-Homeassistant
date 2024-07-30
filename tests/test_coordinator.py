import pytest

from custom_components.hubspace import const, coordinator

from .utils import create_devices_from_data

door_lock = create_devices_from_data("door-lock-TBD.json")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device,expected",
    [
        (
            door_lock[0],
            [
                const.SENSORS_GENERAL["battery-level"],
            ],
        )
    ],
)
async def test_get_sensors(device, expected):
    res = await coordinator.get_sensors(device)
    assert res == expected
