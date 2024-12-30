import pytest
from aiohubspace import InvalidAuth
from homeassistant import config_entries, setup
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hubspace import POLLING_TIME_STR, const


@pytest.fixture
def config_entry(hass):
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
    yield hass, v1_config_entry


@pytest.fixture
def mocked_config_flow(mocked_bridge, mocker):
    mocker.patch(
        "custom_components.hubspace.config_flow.HubspaceBridgeV1",
        return_value=mocked_bridge,
    )
    yield mocked_bridge


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,side_effect,expected_code,expected_data,expected_options",
    [
        # Happy path
        (
            {
                CONF_USERNAME: "cool",
                CONF_PASSWORD: "beans",
                POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
                CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
            },
            None,
            None,
            {CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
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
            },
            None,
            None,
            {CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
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
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == expected_data[CONF_USERNAME]
        assert result["data"] == expected_data
        assert result["options"] == expected_options
    else:
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == expected_code
