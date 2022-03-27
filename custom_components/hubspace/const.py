"""Hubspace constant variables."""

from enum import Enum
from typing import Final

# JSON Keys
DEVICE_ID: Final = "id"
DEVICE_DESCRIPTION: Final = "description"
DEVICE_STATE: Final = "state"
STATE_VALUES: Final = "values"
FUNCTION_CLASS: Final = "functionClass"
FUNCTION_INSTANCE: Final = "functionInstance"

# Function Classes
class FunctionClass:
    UNSUPPORTED = "unsupported"
    POWER = "power"
    BRIGHTNESS = "brightness"
    FAN_SPEED = "fan-speed"
    AVAILABLE = "available"
    TOGGLE = "toggle"


# Function Instances
class FunctionInstance:
    UNSUPPORTED = "unsupported"
    LIGHT_POWER = "light-power"
    FAN_POWER = "fan-power"
    FAN_SPEED = "fan-speed"
    COMFORT_BREEZE = "comfort-breeze"


# Function Key
FunctionKey = tuple[FunctionClass or None, FunctionInstance or None]
