import pytest
from custom_components.hubspace.bridge import HubspaceBridge, InvalidAuth
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from aiohttp import ClientError


@pytest.mark.asyncio
async def test_initialize_bridge_invalid_auth(mocked_entry, mocker):
    hass, entry, mocked_bridge = mocked_entry
    mocker.patch.object(mocked_bridge, "initialize", side_effect=mocker.AsyncMock(side_effect=InvalidAuth))
    mocker.patch("custom_components.hubspace.bridge.create_config_flow")
    bridge = HubspaceBridge(hass, entry)
    async with entry.setup_lock:
        assert await bridge.async_initialize_bridge() is False


@pytest.mark.asyncio
async def test_initialize_bridge_timeout(mocked_entry, mocker):
    hass, entry, mocked_bridge = mocked_entry
    mocker.patch.object(mocked_bridge, "initialize", side_effect=mocker.AsyncMock(side_effect=TimeoutError))
    mocker.patch("custom_components.hubspace.bridge.create_config_flow")
    bridge = HubspaceBridge(hass, entry)
    with pytest.raises(ConfigEntryNotReady):
        async with entry.setup_lock:
            await bridge.async_initialize_bridge()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result, side_effect, msg", [
        # All good
        ("cool beans", None, None),
        # ClientError
        (None, ClientError, "Request failed due connection error"),
        # Generic
        (None, IndexError, "Request failed:"),
    ]
)
async def test_request_call(result, side_effect, msg, caplog, mocker, mocked_entry):
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
