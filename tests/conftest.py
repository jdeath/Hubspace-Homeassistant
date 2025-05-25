"""Helper functions when executing pytest."""

import datetime
import logging

from aioafero import v1
from aioafero.v1.auth import token_data
from aioafero.v1.controllers.event import EventType
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace.const import (
    DEFAULT_POLLING_INTERVAL_SEC,
    DOMAIN,
    POLLING_TIME_STR,
    VERSION_MAJOR,
    VERSION_MINOR,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ensure custom integrations are enabled for testing."""
    return


@pytest.fixture
async def mocked_bridge(mocker) -> v1.AferoBridgeV1:
    """Create a mocked afero bridge to be used in tests."""
    hs_bridge: v1.AferoBridgeV1 = v1.AferoBridgeV1("username2", "password2")
    mocker.patch.object(
        hs_bridge,
        "get_account_id",
        side_effect=mocker.AsyncMock(return_value="mocked-account-id"),
    )
    mocker.patch.object(hs_bridge, "_account_id", "mocked-account-id")
    mocker.patch.object(hs_bridge, "request", side_effect=mocker.AsyncMock())
    mocker.patch.object(hs_bridge, "close", side_effect=mocker.AsyncMock())
    hs_bridge.set_token_data(
        token_data(
            "mock-token",
            "mock-access",
            "mock-refresh-token",
            expiration=datetime.datetime.now().timestamp() + 200,
        )
    )
    mocker.patch.object(
        hs_bridge, "fetch_data", side_effect=mocker.AsyncMock(return_value=[])
    )
    mocker.patch("aioafero.v1.controllers.event.EventStream.initialize")
    await hs_bridge.initialize()

    # Enable ad-hoc event updates
    def emit_event(event_type, data):
        hs_bridge.events.emit(EventType(event_type), data)

    hs_bridge.emit_event = emit_event
    # Override context manager
    hs_bridge.__aenter__ = mocker.AsyncMock(return_value=hs_bridge)
    hs_bridge.__aexit__ = mocker.AsyncMock()
    return hs_bridge


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
    return hass, entry, mocked_bridge


@pytest.fixture(autouse=True)
def set_debug_mode(caplog):
    """Ensure all tests run in debug."""
    # Force capture of all debug logging. This is useful if you want to verify
    # log messages with `<message> in caplog.text`. If you run
    # pytest -rP it will display all log messages, including passing tests.
    caplog.set_level(logging.DEBUG)
