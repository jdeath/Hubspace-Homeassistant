"""Helper functions when executing pytest."""

import asyncio
import datetime
import logging

from aioafero import AferoDevice, v1
from aioafero.v1.auth import TokenData
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace.const import (
    CONF_CLIENT,
    DEFAULT_CLIENT,
    DEFAULT_POLLING_INTERVAL_SEC,
    DOMAIN,
    POLLING_TIME_STR,
    VERSION_MAJOR,
    VERSION_MINOR,
)

from .utils import hs_raw_from_device


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ensure custom integrations are enabled for testing."""
    return


@pytest.fixture
async def mocked_bridge(mocker) -> v1.AferoBridgeV1:
    """Create a mocked afero bridge to be used in tests."""
    mocker.patch("aioafero.v1.controllers.event.EventStream.gather_data")

    bridge: v1.AferoBridgeV1 = v1.AferoBridgeV1("username2", "password2")
    mocker.patch.object(bridge, "_account_id", "mocked-account-id")
    mocker.patch.object(bridge, "fetch_data", return_value=[])
    mocker.patch.object(bridge, "request", side_effect=mocker.AsyncMock())
    mocker.patch.object(
        bridge, "fetch_data", side_effect=mocker.AsyncMock(return_value=[])
    )

    bridge.set_token_data(
        TokenData(
            "mock-token",
            "mock-access",
            "mock-refresh-token",
            expiration=datetime.datetime.now().timestamp() + 200,
        )
    )

    # Enable ad-hoc polls
    async def generate_events_from_data(data):
        task = asyncio.create_task(bridge.events.generate_events_from_data(data))
        await task
        raw_data = await bridge.events.generate_events_from_data(data)
        mocker.patch(
            "aioafero.v1.controllers.event.EventStream.gather_data",
            return_value=raw_data,
        )
        await bridge.async_block_until_done()

    # Fake a poll for discovery
    async def generate_devices_from_data(devices: list[AferoDevice]):
        raw_data = [hs_raw_from_device(device) for device in devices]
        mocker.patch(
            "aioafero.v1.controllers.event.EventStream.gather_data",
            return_value=raw_data,
        )
        await bridge.events.generate_events_from_data(raw_data)
        await bridge.async_block_until_done()

    bridge.generate_devices_from_data = generate_devices_from_data
    bridge.generate_events_from_data = generate_events_from_data

    await bridge.initialize()
    yield bridge
    await bridge.close()


@pytest.fixture
async def mocked_entry(hass, mocker, mocked_bridge) -> MockConfigEntry:
    """Register plugin with a config entry."""
    # Prepare the entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "username",
            CONF_PASSWORD: "password",
            CONF_TOKEN: "mock-token",
            CONF_CLIENT: DEFAULT_CLIENT,
        },
        options={
            CONF_TIMEOUT: 30,
            POLLING_TIME_STR: DEFAULT_POLLING_INTERVAL_SEC,
        },
        version=VERSION_MAJOR,
        minor_version=VERSION_MINOR,
    )
    entry.add_to_hass(hass)
    mocker.patch(
        "custom_components.hubspace.bridge.AferoBridgeV1", return_value=mocked_bridge
    )
    yield hass, entry, mocked_bridge
    await mocked_bridge.close()


@pytest.fixture(autouse=True)
def set_debug_mode(caplog):
    """Ensure all tests run in debug."""
    # Force capture of all debug logging. This is useful if you want to verify
    # log messages with `<message> in caplog.text`. If you run
    # pytest -rP it will display all log messages, including passing tests.
    caplog.set_level(logging.DEBUG)
