import pytest

from custom_components.hubspace import const, coordinator

from .utils import create_devices_from_data

door_lock = create_devices_from_data("door-lock-TBD.json")
freezer = create_devices_from_data("freezer.json")[0]


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device,expected",
    [
        (
            freezer,
            [
                const.BINARY_SENSORS["freezer"]["error|mcu-communication-failure"],
                const.BINARY_SENSORS["freezer"]["error|fridge-high-temperature-alert"],
                const.BINARY_SENSORS["freezer"]["error|freezer-high-temperature-alert"],
                const.BINARY_SENSORS["freezer"]["error|temperature-sensor-failure"],
            ],
        ),
    ],
)
async def test_get_binary_sensors(device, expected):
    assert await coordinator.get_binary_sensors(device) == expected
