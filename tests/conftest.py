import datetime
import logging

import pytest
from aiohubspace import v1
from aiohubspace.v1.auth import token_data
from aiohubspace.v1.controllers.event import EventType
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
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
    yield


@pytest.fixture(scope="function")
async def mocked_bridge(mocker) -> v1.HubspaceBridgeV1:
    hs_bridge: v1.HubspaceBridgeV1 = v1.HubspaceBridgeV1("username2", "password2")
    mocker.patch.object(
        hs_bridge,
        "get_account_id",
        side_effect=mocker.AsyncMock(return_value="mocked-account-id"),
    )
    mocker.patch.object(hs_bridge, "_account_id", "mocked-account-id")
    mocker.patch.object(hs_bridge, "request", side_effect=mocker.AsyncMock())
    mocker.patch.object(hs_bridge, "initialize", side_effect=mocker.AsyncMock())
    mocker.patch.object(hs_bridge, "close", side_effect=mocker.AsyncMock())
    hs_bridge._auth._token_data = token_data(
        "mock-token", expiration=datetime.datetime.now().timestamp() + 200
    )
    hs_bridge._auth._refresh_token = "mock-refresh-token"
    # Force initialization so test elements are not overwritten
    for controller in hs_bridge._controllers:
        controller._initialized = True

    # Enable ad-hoc event updates
    def emit_event(event_type, data):
        hs_bridge.events.emit(EventType(event_type), data)

    hs_bridge.emit_event = emit_event
    # Override context manager
    hs_bridge.__aenter__ = mocker.AsyncMock(return_value=hs_bridge)
    hs_bridge.__aexit__ = mocker.AsyncMock()
    # Ensure its "fake" initialized
    for controller in hs_bridge.controllers:
        res_filter = tuple(x.value for x in controller.ITEM_TYPES)
        if res_filter:
            hs_bridge.events.subscribe(
                controller._handle_event,
                resource_filter=res_filter,
            )
        else:
            # Subscribe to all events
            hs_bridge.events.subscribe(
                controller._handle_event,
            )
    yield hs_bridge


@pytest.fixture(scope="function")
async def mocked_entry(hass, mocker, mocked_bridge) -> MockConfigEntry:
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
        "custom_components.hubspace.bridge.HubspaceBridgeV1", return_value=mocked_bridge
    )
    return hass, entry, mocked_bridge


@pytest.fixture(autouse=True)
def set_debug_mode(caplog):
    # Force capture of all debug logging. This is useful if you want to verify
    # log messages with `<message> in caplog.text`. If you run
    # pytest -rP it will display all log messages, including passing tests.
    caplog.set_level(logging.DEBUG)
