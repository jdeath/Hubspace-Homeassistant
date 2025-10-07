"""Test the plugins initialization tasks."""

from aioafero.errors import InvalidAuth
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_TOKEN, CONF_USERNAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import hubspace
from custom_components.hubspace import const


@pytest.fixture(autouse=True)
def hubspace_migration(mocked_bridge, mocker):
    """Mock the Bridge."""
    mocker.patch("custom_components.hubspace.AferoBridgeV1", return_value=mocked_bridge)
    return mocked_bridge


@pytest.fixture
def v1_config_entry(hass):
    """Register a v1 config entry."""
    v1_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
        options={},
        unique_id=None,
        version=1,
        minor_version=0,
    )
    v1_config_entry.add_to_hass(hass)
    return hass, v1_config_entry


@pytest.fixture
def v2_config_entry(hass):
    """Register a v2 config entry."""
    v2_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={
            CONF_USERNAME: "cool",
            CONF_PASSWORD: "beans",
            CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
        },
        options={},
        version=2,
        minor_version=0,
    )
    v2_config_entry.add_to_hass(hass)
    return hass, v2_config_entry


@pytest.fixture
def v2_config_entry_custom(hass):
    """Register a v2 config entry with a custom timeout."""
    v2_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={CONF_USERNAME: "cool", CONF_PASSWORD: "beans", CONF_TIMEOUT: 42},
        options={},
        version=2,
        minor_version=0,
    )
    v2_config_entry.add_to_hass(hass)
    return hass, v2_config_entry


@pytest.fixture
def v3_config_entry(hass):
    """Register a v3 config entry."""
    v3_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={
            CONF_USERNAME: "cool",
            CONF_PASSWORD: "beans",
        },
        options={
            CONF_TIMEOUT: 10000,
            const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
        },
        version=3,
        minor_version=0,
    )
    v3_config_entry.add_to_hass(hass)
    return hass, v3_config_entry


@pytest.fixture
def v4_config_entry(hass):
    """Register a v4 config entry."""
    v4_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={
            CONF_USERNAME: "cool",
            CONF_PASSWORD: "beans",
            CONF_TOKEN: "mock-refresh-token",
        },
        options={
            CONF_TIMEOUT: 10000,
            const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
        },
        version=4,
        minor_version=0,
    )
    v4_config_entry.add_to_hass(hass)
    return hass, v4_config_entry


@pytest.fixture
def v5_config_entry(hass):
    """Register a v5 config entry."""
    v5_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={
            CONF_USERNAME: "cool",
            CONF_PASSWORD: "beans",
            CONF_TOKEN: "mock-refresh-token",
            const.CONF_CLIENT: const.DEFAULT_CLIENT,
        },
        options={
            CONF_TIMEOUT: 10000,
            const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
        },
        version=5,
        minor_version=0,
    )
    v5_config_entry.add_to_hass(hass)
    return hass, v5_config_entry


@pytest.mark.asyncio
async def test_async_migrate_entry(v1_config_entry):
    """Test configuration migration."""
    assert await hubspace.async_migrate_entry(v1_config_entry[0], v1_config_entry[1])
    assert v1_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
        CONF_TOKEN: "mock-refresh-token",
        const.CONF_CLIENT: const.DEFAULT_CLIENT,
    }
    assert v1_config_entry[1].options == {
        CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v1_config_entry[1].version == const.VERSION_MAJOR


@pytest.mark.asyncio
async def test_perform_v2_migration(v1_config_entry):
    """Test configuration migration from v1 to v2."""
    await hubspace.perform_v2_migration(v1_config_entry[0], v1_config_entry[1])
    assert v1_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
        CONF_TIMEOUT: 10000,
    }
    assert v1_config_entry[1].options == {}
    assert v1_config_entry[1].version == 2
    assert v1_config_entry[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v3_migration_from_v1(v1_config_entry):
    """Test configuration migration from v1 to v3."""
    await hubspace.perform_v3_migration(v1_config_entry[0], v1_config_entry[1])
    assert v1_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
    }
    assert v1_config_entry[1].options == {
        CONF_TIMEOUT: 10000,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v1_config_entry[1].unique_id == "cool"
    assert v1_config_entry[1].version == 3
    assert v1_config_entry[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v3_migration_from_v2(v2_config_entry):
    """Test configuration migration from v2 to v3."""
    await hubspace.perform_v3_migration(v2_config_entry[0], v2_config_entry[1])
    assert v2_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
    }
    assert v2_config_entry[1].options == {
        CONF_TIMEOUT: 10000,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v2_config_entry[1].unique_id == "cool"
    assert v2_config_entry[1].version == 3
    assert v2_config_entry[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v3_migration_from_v2_custom(v2_config_entry_custom):
    """Test configuration migration from v2 to v3 with custom timeout."""
    await hubspace.perform_v3_migration(
        v2_config_entry_custom[0], v2_config_entry_custom[1]
    )
    assert v2_config_entry_custom[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
    }
    assert v2_config_entry_custom[1].options == {
        CONF_TIMEOUT: 42,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v2_config_entry_custom[1].unique_id == "cool"
    assert v2_config_entry_custom[1].title == "cool"
    assert v2_config_entry_custom[1].version == 3
    assert v2_config_entry_custom[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v4_migration_from_v3(v3_config_entry):
    """Test configuration migration from v3 to v4."""
    await hubspace.perform_v4_migration(v3_config_entry[0], v3_config_entry[1])
    assert v3_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
        CONF_TOKEN: "mock-refresh-token",
    }
    assert v3_config_entry[1].options == {
        CONF_TIMEOUT: 10000,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v3_config_entry[1].unique_id == "cool"
    assert v3_config_entry[1].version == 4
    assert v3_config_entry[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v4_migration_from_v3_with_err(
    v3_config_entry, hubspace_migration, mocker
):
    """Test configuration migration from v3 to v4 but contains an error."""
    mocker.patch.object(hubspace_migration, "get_account_id", side_effect=InvalidAuth())
    await hubspace.perform_v4_migration(v3_config_entry[0], v3_config_entry[1])
    assert v3_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
    }
    assert v3_config_entry[1].options == {
        CONF_TIMEOUT: 10000,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }
    assert v3_config_entry[1].unique_id is None
    assert v3_config_entry[1].version == 3
    assert v3_config_entry[1].minor_version == 0


@pytest.mark.asyncio
async def test_perform_v5_migration_from_v4(v4_config_entry):
    """Test configuration migration from v4 to v5."""
    await hubspace.perform_v5_migration(v4_config_entry[0], v4_config_entry[1])
    assert v4_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
        CONF_TOKEN: "mock-refresh-token",
        const.CONF_CLIENT: const.DEFAULT_CLIENT,
    }
    assert v4_config_entry[1].version == 5
    assert v4_config_entry[1].minor_version == 0
