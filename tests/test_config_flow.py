"""Test config flow use cases."""

import sys

from aioafero import InvalidAuth
from homeassistant import config_entries, setup
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace import POLLING_TIME_STR, const


@pytest.fixture
def config_entry(hass):
    """Fixture that registered a default config entry."""
    v1_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
        options={
            CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
        },
        unique_id="cool",
    )
    v1_config_entry.add_to_hass(hass)
    return hass, v1_config_entry


@pytest.fixture
def mocked_config_flow(mocked_bridge, mocker):
    """Fixture for getting the mocked bridge."""
    mocker.patch(
        "custom_components.hubspace.config_flow.AferoBridgeV1",
        return_value=mocked_bridge,
    )
    return mocked_bridge


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "data",
        "side_effect",
        "expected_code",
        "expected_data",
        "expected_options",
    ),
    [
        # Happy path
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            None,
            None,
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                CONF_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
        ),
        # Happy path without CONF_TIMEOUT or POLLING_TIME_STR
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: 0,
                CONF_TIMEOUT: 0,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            None,
            None,
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                CONF_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
        ),
        # Poll cycle is too short
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: 1,
                CONF_TIMEOUT: 0,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            None,
            "polling_too_short",
            None,
            None,
        ),
        # Timeout
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            TimeoutError,
            "cannot_connect",
            None,
            None,
        ),
        # Timeout
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            InvalidAuth,
            "invalid_auth",
            None,
            None,
        ),
        # Weird issues happen
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            KeyError,
            "unknown",
            None,
            None,
        ),
    ],
)
async def test_HubspaceConfigFlow_async_step_user(
    data,
    side_effect,
    expected_code,
    expected_data,
    expected_options,
    mocked_config_flow,
    mocker,
    hass,
):
    """Ensure config flow properly handles user setup."""
    if side_effect:
        mocker.patch.object(
            mocked_config_flow,
            "get_account_id",
            side_effect=mocker.AsyncMock(side_effect=side_effect),
        )
    await setup.async_setup_component(hass, const.DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=data,
    )

    if not side_effect and not expected_code:
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == expected_data[CONF_USERNAME]
        assert result["data"] == expected_data
        assert result["options"] == expected_options
    else:
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == expected_code


@pytest.mark.parametrize(
    (
        "config_dict",
        "user_data",
        "expected_data",
        "expected_options",
        "expected_code",
        "error_code",
    ),
    [
        # Reauth happy path
        pytest.param(
            {
                "data": {
                    CONF_USERNAME: "cool",
                    CONF_PASSWORD: "beans",
                    const.CONF_CLIENT: const.DEFAULT_CLIENT,
                },
                "options": {
                    POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                    CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                },
                "unique_id": "cool",
            },
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans2",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans2",
                CONF_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            "reauth_successful",
            None,
            marks=pytest.mark.skipif(
                sys.version_info <= (3, 13), reason="DNS issues on 3.12"
            ),
        ),
        # Changing username
        (
            {
                "data": {
                    CONF_USERNAME: "cool",
                    CONF_PASSWORD: "beans",
                    const.CONF_CLIENT: const.DEFAULT_CLIENT,
                },
                "options": {
                    POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                    CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                },
                "unique_id": "cool",
            },
            {
                CONF_USERNAME: "cool2",
                CONF_PASSWORD: "beans2",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans2",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            None,
            "unique_id_mismatch",
        ),
    ],
)
async def test_HubspaceConfigFlow_async_step_user_reauth(
    config_dict,
    user_data,
    expected_data,
    expected_options,
    expected_code,
    error_code,
    mocked_config_flow,
    mocker,
    hass,
):
    """Ensure config flow properly handles re-auth requests."""
    await setup.async_setup_component(hass, const.DOMAIN, {})
    config_dict["domain"] = const.DOMAIN
    config_dict["source"] = config_entries.SOURCE_REAUTH
    entry = MockConfigEntry(**config_dict)
    entry.add_to_hass(hass)
    # Start the reauth
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    # Accept the second popup
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    # Set the new data
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_data,
    )

    if error_code:
        assert result["errors"]["base"] == error_code
    else:
        assert result["reason"] == expected_code
        assert entry.data == expected_data
        assert entry.options == expected_options


@pytest.mark.parametrize(
    (
        "config_dict",
        "user_data",
        "expected_options",
        "error_code",
    ),
    [
        # Not set
        (
            {
                "data": {CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
                "options": {
                    POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                    CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                },
                "unique_id": "cool",
            },
            {
                POLLING_TIME_STR: 0,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            None,
        ),
        # Too short
        (
            {
                "data": {CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
                "options": {
                    POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                    CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                },
                "unique_id": "cool",
            },
            {
                POLLING_TIME_STR: 1,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            "polling_too_short",
        ),
    ],
)
async def test_HubspaceConfigFlow_async_step_options(
    config_dict,
    user_data,
    expected_options,
    error_code,
    mocked_config_flow,
    mocker,
    hass,
):
    """Ensure config flow properly handles all use-cases."""
    await setup.async_setup_component(hass, const.DOMAIN, {})
    config_dict["domain"] = const.DOMAIN
    entry = MockConfigEntry(**config_dict)
    entry.add_to_hass(hass)
    # Start options
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # Accept the second popup
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=user_data,
    )
    if error_code:
        assert result["errors"]["base"] == error_code
    else:
        assert entry.options == expected_options
