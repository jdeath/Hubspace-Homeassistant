from datetime import timedelta
from typing import Final

DOMAIN = "hubspace"
CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"
UPDATE_INTERVAL_OBSERVATION = timedelta(seconds=30)
HUB_IDENTIFIER: Final[str] = "hubspace_debug"