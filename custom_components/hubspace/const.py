from datetime import timedelta
from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    Platform,
    UnitOfElectricPotential,
    UnitOfPower,
)

DOMAIN = "hubspace"
CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"
UPDATE_INTERVAL_OBSERVATION = timedelta(seconds=30)
HUB_IDENTIFIER: Final[str] = "hubspace_debug"
DEFAULT_TIMEOUT: Final[int] = 10000
DEFAULT_POLLING_INTERVAL_SEC: Final[int] = 30
POLLING_TIME_STR: Final[str] = "polling_time"

VERSION_MAJOR: Final[int] = 4
VERSION_MINOR: Final[int] = 0


PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


ENTITY_BINARY_SENSOR: Final[str] = "binary_sensor"
ENTITY_CLIMATE: Final[str] = "climate"
ENTITY_FAN: Final[str] = "fan"
ENTITY_LIGHT: Final[str] = "light"
ENTITY_LOCK: Final[str] = "lock"
ENTITY_SENSOR: Final[str] = "sensor"
ENTITY_SWITCH: Final[str] = "switch"
ENTITY_VALVE: Final[str] = "valve"

DEVICE_CLASS_FAN: Final[str] = "fan"
DEVICE_CLASS_FREEZER: Final[str] = "freezer"
DEVICE_CLASS_LIGHT: Final[str] = "light"
DEVICE_CLASS_SWITCH: Final[str] = "switch"
DEVICE_CLASS_OUTLET: Final[str] = "power-outlet"
DEVICE_CLASS_LANDSCAPE_TRANSFORMER: Final[str] = "landscape-transformer"
DEVICE_CLASS_DOOR_LOCK: Final[str] = "door-lock"
DEVICE_CLASS_WATER_TIMER: Final[str] = "water-timer"

DEVICE_CLASS_TO_ENTITY_MAP: Final[dict[str, str]] = {
    DEVICE_CLASS_FREEZER: ENTITY_CLIMATE,
    DEVICE_CLASS_FAN: ENTITY_FAN,
    DEVICE_CLASS_LIGHT: ENTITY_LIGHT,
    DEVICE_CLASS_DOOR_LOCK: ENTITY_LOCK,
    DEVICE_CLASS_SWITCH: ENTITY_SWITCH,
    DEVICE_CLASS_OUTLET: ENTITY_SWITCH,
    DEVICE_CLASS_LANDSCAPE_TRANSFORMER: ENTITY_SWITCH,
    DEVICE_CLASS_WATER_TIMER: ENTITY_VALVE,
}

UNMAPPED_DEVICE_CLASSES: Final[list[str]] = [
    # Parent device for a fan / light combo
    "ceiling-fan",
]


# Sensors that apply to any device that it is found on
SENSORS_GENERAL = {
    "battery-level": SensorEntityDescription(
        key="battery-level",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "output-voltage-switch": SensorEntityDescription(
        key="output-voltage-switch",
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "watts": SensorEntityDescription(
        key="watts",
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "wifi-rssi": SensorEntityDescription(
        key="wifi-rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}

BINARY_SENSORS = {
    "error|mcu-communication-failure": BinarySensorEntityDescription(
        key="error|mcu-communication-failure",
        name="MCU",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "error|fridge-high-temperature-alert": BinarySensorEntityDescription(
        key="error|fridge-high-temperature-alert",
        name="Fridge High Temp Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "error|freezer-high-temperature-alert": BinarySensorEntityDescription(
        key="error|freezer-high-temperature-alert",
        name="Freezer High Temp Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "error|temperature-sensor-failure": BinarySensorEntityDescription(
        key="error|temperature-sensor-failure",
        name="Sensor Failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}
