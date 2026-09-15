"""Test the bridge between Home Assistant and Afero."""

from aiohttp import ClientError
from homeassistant.const import CONF_TIMEOUT, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace.bridge import HubspaceBridge, InvalidAuth
from custom_components.hubspace.const import (
    CONF_CLIENT,
    CONF_ENABLE_CONCLAVE,
    CONF_REFRESH_TOKEN,
    DEFAULT_CLIENT,
    DEFAULT_POLLING_INTERVAL_SEC,
    DOMAIN,
    POLLING_TIME_STR,
    VERSION_MAJOR,
    VERSION_MINOR,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({}, True),
        ({CONF_ENABLE_CONCLAVE: True}, True),
        ({CONF_ENABLE_CONCLAVE: False}, False),
    ],
)
async def test_bridge_enable_conclave_option(
    options, expected, hass, mocker, mocked_bridge
):
    """Conclave is on by default; options can opt out."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "username",
            CONF_REFRESH_TOKEN: "mock-token",
            CONF_CLIENT: DEFAULT_CLIENT,
        },
        options={
            CONF_TIMEOUT: 30,
            POLLING_TIME_STR: DEFAULT_POLLING_INTERVAL_SEC,
            **options,
        },
        version=VERSION_MAJOR,
        minor_version=VERSION_MINOR,
    )
    entry.add_to_hass(hass)
    captured: dict = {}

    def _capture(*args, **kwargs):
        captured["kwargs"] = kwargs
        return mocked_bridge

    mocker.patch(
        "custom_components.hubspace.bridge.AferoBridgeV1",
        side_effect=_capture,
    )
    HubspaceBridge(hass, entry)
    assert captured["kwargs"].get("enable_conclave") is expected


@pytest.mark.asyncio
async def test_initialize_bridge_invalid_auth(mocked_entry, mocker):
    """Ensure the bridge is not initialized when auth fails."""
    hass, entry, mocked_bridge = mocked_entry
    mocker.patch.object(
        mocked_bridge,
        "initialize",
        side_effect=mocker.AsyncMock(side_effect=InvalidAuth),
    )
    mocker.patch("custom_components.hubspace.bridge.create_config_flow")
    bridge = HubspaceBridge(hass, entry)
    async with entry.setup_lock:
        assert await bridge.async_initialize_bridge() is False


@pytest.mark.asyncio
async def test_initialize_bridge_timeout(mocked_entry, mocker):
    """Ensure a timeout during initialization marks the entry as failed."""
    hass, entry, mocked_bridge = mocked_entry
    mocker.patch.object(
        mocked_bridge,
        "initialize",
        side_effect=mocker.AsyncMock(side_effect=TimeoutError),
    )
    mocker.patch("custom_components.hubspace.bridge.create_config_flow")
    bridge = HubspaceBridge(hass, entry)
    with pytest.raises(ConfigEntryNotReady):
        async with entry.setup_lock:
            await bridge.async_initialize_bridge()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "result",
        "side_effect",
        "msg",
    ),
    [
        # All good
        ("cool beans", None, None),
        # ClientError
        (None, ClientError, "Request failed due connection error"),
        # Generic
        (None, IndexError, "Request failed:"),
    ],
)
async def test_request_call(result, side_effect, msg, caplog, mocker, mocked_entry):
    """Ensure the bridge correctly creates the request task."""
    hass, entry, mocked_bridge = mocked_entry
    bridge = HubspaceBridge(hass, entry)
    if result:
        task = mocker.AsyncMock(return_value=result)
    else:
        task = mocker.AsyncMock(side_effect=side_effect)
    if side_effect:
        with pytest.raises(HomeAssistantError, match=msg):
            await bridge.async_request_call(task)
    else:
        await bridge.async_request_call(task)
