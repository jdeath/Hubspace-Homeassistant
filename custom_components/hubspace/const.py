from datetime import timedelta
from typing import Final

DOMAIN = "hubspace"
CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"
UPDATE_INTERVAL_OBSERVATION = timedelta(seconds=30)
HUB_IDENTIFIER: Final[str] = "hubspace_debug"


ENTITY_FAN: Final[str] = "fan"
ENTITY_LIGHT: Final[str] = "light"
ENTITY_LOCK: Final[str] = "lock"
ENTITY_SWITCH: Final[str] = "switch"
ENTITY_VALVE: Final[str] = "valve"

DEVICE_CLASS_FAN: Final[str] = "fan"
DEVICE_CLASS_LIGHT: Final[str] = "light"
DEVICE_CLASS_SWITCH: Final[str] = "switch"
DEVICE_CLASS_OUTLET: Final[str] = "power-outlet"
DEVICE_CLASS_LANDSCAPE_TRANSFORMER: Final[str] = "landscape-transformer"
DEVICE_CLASS_DOOR_LOCK: Final[str] = "door-lock"
DEVICE_CLASS_WATER_TIMER: Final[str] = "water-timer"

DEVICE_CLASS_TO_ENTITY_MAP: Final[dict[str, str]] = {
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