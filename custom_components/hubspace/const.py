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
class FunctionClass(Enum):
    UNSUPPORTED = "unsupported"
    POWER = "power"
    BRIGHTNESS = "brightness"
    FAN_SPEED = "fan-speed"
    AVAILABLE = "available"

    @classmethod
    def _missing_(cls, value):
        if value:
            return FunctionClass.UNSUPPORTED
        return None


# Function Instances
class FunctionInstance(Enum):
    UNSUPPORTED = "unsupported"
    LIGHT_POWER = "light-power"
    FAN_POWER = "fan-power"
    FAN_SPEED = "fan-speed"

    @classmethod
    def _missing_(cls, value):
        if value:
            return FunctionInstance.UNSUPPORTED
        return None


# Function Key
FunctionKey = tuple[FunctionClass or None, FunctionInstance or None]
