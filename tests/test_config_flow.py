"""Test config flow use cases."""

import sys

from aioafero import InvalidAuth, InvalidOTP, OTPRequired
from homeassistant import config_entries, setup
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace import POLLING_TIME_STR, const
from custom_components.hubspace.const import CONF_ENABLE_CONCLAVE, CONF_REFRESH_TOKEN


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
def mocked_config_flow(mocker):
    """Fixture that mocks AferoAuth.for_login for config-flow tests."""
    token_data = mocker.Mock()
    token_data.refresh_token = "mock-refresh-token"
    auth = mocker.Mock()
    auth.login = mocker.AsyncMock(return_value=token_data)
    auth.submit_otp = mocker.AsyncMock(return_value=token_data)
    mocker.patch(
        "custom_components.hubspace.config_flow.AferoAuth.for_login",
        return_value=auth,
    )
    return auth


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
                CONF_REFRESH_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: True,
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
                CONF_REFRESH_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: True,
            },
        ),
        # Opt out of Conclave at setup
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
                CONF_ENABLE_CONCLAVE: False,
            },
            None,
            None,
            {
                CONF_USERNAME: "cool",
                CONF_REFRESH_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: False,
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
        # Invalid auth provided
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
            "login",
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
                CONF_PASSWORD: "beans2",
            },
            {
                CONF_USERNAME: "cool",
                CONF_REFRESH_TOKEN: "mock-refresh-token",
                const.CONF_CLIENT: const.DEFAULT_CLIENT,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: True,
            },
            "reauth_successful",
            None,
            marks=pytest.mark.skipif(
                sys.version_info <= (3, 13), reason="DNS issues on 3.12"
            ),
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
                CONF_ENABLE_CONCLAVE: True,
            },
            None,
        ),
        # Opt out of Conclave via options
        (
            {
                "data": {CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
                "options": {
                    POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                    CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                    CONF_ENABLE_CONCLAVE: True,
                },
                "unique_id": "cool",
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: False,
            },
            {
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
                CONF_ENABLE_CONCLAVE: False,
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


async def test_HubspaceConfigFlow_otp_flow(hass, mocker, mocked_config_flow):
    """Ensure OTP flow works."""
    mocker.patch.object(
        mocked_config_flow,
        "login",
        side_effect=mocker.AsyncMock(side_effect=OTPRequired),
    )
    await setup.async_setup_component(hass, const.DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    user_data = {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
        POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
        CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
        const.CONF_CLIENT: const.DEFAULT_CLIENT,
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_data,
    )
    # Verify OTP is prompted
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "otp"
    # Accept the OTP popup
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
    )
    # Submit the OTP form and show an unexpected exception
    mocker.patch.object(
        mocked_config_flow,
        "submit_otp",
        side_effect=mocker.AsyncMock(side_effect=ValueError),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CONF_OTP: "123456"},
    )
    assert result["errors"]["base"] == "unknown_otp"
    # Submit an invalid OTP
    mocker.patch.object(
        mocked_config_flow,
        "submit_otp",
        side_effect=mocker.AsyncMock(side_effect=InvalidOTP),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CONF_OTP: "123456"},
    )
    assert result["errors"]["base"] == "invalid_otp"
    # Submit a valid OTP
    token_data = mocker.Mock()
    token_data.refresh_token = "mock-refresh-token"
    mocker.patch.object(
        mocked_config_flow,
        "submit_otp",
        side_effect=mocker.AsyncMock(return_value=token_data),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CONF_OTP: "123456"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == user_data[CONF_USERNAME]
    assert result["data"] == {
        CONF_USERNAME: user_data[CONF_USERNAME],
        CONF_REFRESH_TOKEN: "mock-refresh-token",
        const.CONF_CLIENT: user_data[const.CONF_CLIENT],
    }
    assert result["options"] == {
        POLLING_TIME_STR: user_data[POLLING_TIME_STR],
        CONF_TIMEOUT: user_data[CONF_TIMEOUT],
        CONF_ENABLE_CONCLAVE: True,
    }
