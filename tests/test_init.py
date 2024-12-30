import pytest
from homeassistant.const import CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import hubspace
from custom_components.hubspace import const


@pytest.fixture
def v1_config_entry(hass):
    v1_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={CONF_USERNAME: "cool", CONF_PASSWORD: "beans"},
        options={},
        unique_id=None,
    )
    v1_config_entry.add_to_hass(hass)
    yield hass, v1_config_entry


@pytest.fixture
def v2_config_entry(hass):
    v1_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={
            CONF_USERNAME: "cool",
            CONF_PASSWORD: "beans",
            CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
        },
        options={},
    )
    v1_config_entry.add_to_hass(hass)
    yield hass, v1_config_entry


@pytest.fixture
def v2_config_entry_custom(hass):
    v1_config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={CONF_USERNAME: "cool", CONF_PASSWORD: "beans", CONF_TIMEOUT: 42},
        options={},
    )
    v1_config_entry.add_to_hass(hass)
    yield hass, v1_config_entry


@pytest.mark.asyncio
async def test_async_migrate_entry(v1_config_entry):
    assert await hubspace.async_migrate_entry(v1_config_entry[0], v1_config_entry[1])
    assert v1_config_entry[1].data == {
        CONF_USERNAME: "cool",
        CONF_PASSWORD: "beans",
    }
    assert v1_config_entry[1].options == {
        CONF_TIMEOUT: const.DEFAULT_TIMEOUT,
        const.POLLING_TIME_STR: const.DEFAULT_POLLING_INTERVAL_SEC,
    }


@pytest.mark.asyncio
async def test_perform_v2_migration(v1_config_entry):

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
