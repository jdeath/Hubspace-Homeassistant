import asyncio
import logging
from typing import Any, Callable

import aiohttp
from aiohttp import client_exceptions
from aiohubspace import HubspaceBridgeV1, InvalidAuth, InvalidResponse
from homeassistant import core
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, PLATFORMS, POLLING_TIME_STR
from .device import async_setup_devices


class HubspaceBridge:
    """Manages a single Hubspace account"""

    def __init__(self, hass: core.HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.authorized = False
        # Jobs to be executed when API is reset.
        self.reset_jobs: list[core.CALLBACK_TYPE] = []
        # self.sensor_manager: SensorManager | None = None
        self.logger = logging.getLogger(__name__)
        polling_interval = int(self.config_entry.options[POLLING_TIME_STR])
        # store actual api connection to bridge as api
        self.api = HubspaceBridgeV1(
            self.config_entry.data[CONF_USERNAME],
            self.config_entry.data[CONF_PASSWORD],
            session=aiohttp_client.async_get_clientsession(hass),
            polling_interval=polling_interval,
        )
        # store (this) bridge object in hass data
        hass.data.setdefault(DOMAIN, {})[self.config_entry.entry_id] = self

    async def async_initialize_bridge(self) -> bool:
        """Initialize Connection with the Hue API."""
        setup_ok = False
        try:
            async with asyncio.timeout(self.config_entry.options[CONF_TIMEOUT]):
                await self.api.initialize()
            setup_ok = True
        except (InvalidAuth, InvalidResponse):
            # Credentials have changed. Force a re-login
            create_config_flow(self.hass, self.config_entry.data[CONF_USERNAME])
            return False
        except (
            TimeoutError,
            client_exceptions.ClientOSError,
            client_exceptions.ServerDisconnectedError,
            client_exceptions.ContentTypeError,
        ) as err:
            raise ConfigEntryNotReady(
                f"Error connecting to the Hubspace API: {err}"
            ) from err
        except Exception:
            self.logger.exception("Unknown error connecting to the Hubspace API")
            return False
        finally:
            if not setup_ok:
                await self.api.close()

        # Init devices
        await async_setup_devices(self)
        await self.hass.config_entries.async_forward_entry_setups(
            self.config_entry, PLATFORMS
        )
        # add listener for config entry updates.
        self.reset_jobs.append(self.config_entry.add_update_listener(_update_listener))
        self.authorized = True
        return True

    async def async_request_call(self, task: Callable, *args, **kwargs) -> Any:
        """Send request to the Hue bridge."""
        try:
            return await task(*args, **kwargs)
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Request failed due connection error: {err}"
            ) from err
        except Exception as err:
            msg = f"Request failed: {err}"
            raise HomeAssistantError(msg) from err

    async def async_reset(self) -> bool:
        """Reset this bridge to default state.

        Will cancel any scheduled setup retry and will unload
        the config entry.
        """

        # If the authentication was wrong.
        if self.api is None:
            return True

        while self.reset_jobs:
            self.reset_jobs.pop()()

        # Unload platforms
        unload_success = await self.hass.config_entries.async_unload_platforms(
            self.config_entry, PLATFORMS
        )

        if unload_success:
            self.hass.data[DOMAIN].pop(self.config_entry.entry_id)

        return unload_success

    async def handle_unauthorized_error(self) -> None:
        """Create a new config flow when the authorization is no longer valid."""
        if not self.authorized:
            return
        self.logger.error(
            "Unable to authorize to Hubspace, setup the linking again",
        )
        self.authorized = False
        create_config_flow(self.hass, self.config_entry.data[CONF_USERNAME])


async def _update_listener(hass: core.HomeAssistant, entry: ConfigEntry) -> None:
    """Handle ConfigEntry options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def create_config_flow(hass: core.HomeAssistant, username: str) -> None:
    """Start a config flow."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_USERNAME: username},
        )
    )