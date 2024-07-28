from custom_components.hubspace import const, sensor

from .utils import create_devices_from_data

door_lock = create_devices_from_data("door-lock-TBD.json")


def test_sensor(mocked_coordinator):
    empty_sensor = sensor.HubSpaceSensor(
        mocked_coordinator,
        const.SENSORS_GENERAL["battery-level"],
        door_lock[0],
    )
    empty_sensor.coordinator.data[const.ENTITY_SENSOR][door_lock[0].id] = {
        "device": door_lock[0]
    }
    empty_sensor.update_states()
    assert empty_sensor.native_value == 80
