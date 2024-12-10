import pytest

from custom_components.hubspace import const, sensor

from .utils import create_devices_from_data

door_lock = create_devices_from_data("door-lock-TBD.json")
transformer = create_devices_from_data("transformer.json")


@pytest.mark.parametrize(
    "sensor_descr,device,is_numeric,expected",
    [
        (const.SENSORS_GENERAL["battery-level"], door_lock[0], True, 80),
        (const.SENSORS_GENERAL["output-voltage-switch"], transformer[0], True, 12),
        (const.SENSORS_GENERAL["watts"], transformer[0], True, 0),
        (const.SENSORS_GENERAL["wifi-rssi"], transformer[0], True, -51),
    ],
)
def test_sensor(sensor_descr, device, is_numeric, expected, mocked_coordinator, mocker):
    empty_sensor = sensor.HubSpaceSensor(
        mocked_coordinator,
        sensor_descr,
        device,
        is_numeric,
    )
    mocker.patch.object(empty_sensor, "get_device_states", return_value=device.states)
    empty_sensor.update_states()
    # Ensure the state can be correctly calculated
    empty_sensor.state
    assert empty_sensor.native_value == expected
