import pytest

from custom_components.hubspace import binary_sensor, const

from .utils import create_devices_from_data

freezer = create_devices_from_data("freezer.json")[0]


@pytest.mark.parametrize(
    "sensor_descr,device,expected",
    [
        (
            const.BINARY_SENSORS["freezer"]["error|mcu-communication-failure"],
            freezer,
            False,
        ),
        (
            const.BINARY_SENSORS["freezer"]["error|fridge-high-temperature-alert"],
            freezer,
            True,
        ),
    ],
)
def test_sensor(sensor_descr, device, expected, mocked_coordinator):
    empty_sensor = binary_sensor.HubSpaceBinarySensor(
        mocked_coordinator,
        sensor_descr,
        device,
    )
    empty_sensor.coordinator.data[const.ENTITY_BINARY_SENSOR][device.id] = {
        "device": device
    }
    empty_sensor.update_states()
    assert empty_sensor.is_on == expected
