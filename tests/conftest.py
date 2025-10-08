"""Helper functions when executing pytest."""

import logging

from aioafero import v1
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .utils import get_mocked_bridge, get_mocked_entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ensure custom integrations are enabled for testing."""
    return


@pytest.fixture
async def mocked_bridge(mocker) -> v1.AferoBridgeV1:
    """Create a mocked afero bridge to be used in tests."""
    bridge = get_mocked_bridge(mocker)
    await bridge.initialize()
    yield bridge
    await bridge.close()


@pytest.fixture
async def mocked_entry(hass, mocker, mocked_bridge) -> MockConfigEntry:
    """Register plugin with a config entry."""
    hass, entry, mocked_bridge = get_mocked_entry(hass, mocker, mocked_bridge)
    yield hass, entry, mocked_bridge
    await mocked_bridge.close()


@pytest.fixture(autouse=True)
def set_debug_mode(caplog):
    """Ensure all tests run in debug."""
    # Force capture of all debug logging. This is useful if you want to verify
    # log messages with `<message> in caplog.text`. If you run
    # pytest -rP it will display all log messages, including passing tests.
    caplog.set_level(logging.DEBUG)
