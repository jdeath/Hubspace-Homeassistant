import logging

import hubspace_async
import pytest

from custom_components.hubspace import coordinator
from collections import defaultdict


@pytest.fixture
def mocked_coordinator(mocker, mocked_hubspace):
    # The platform doesn't know what to do with async_write_ha_state
    # RuntimeError: Attribute hass is None for <entity unknown.unknown=unknown>
    mocker.patch("homeassistant.helpers.entity.Entity.async_write_ha_state")
    coord_mock = mocker.patch.object(
        coordinator, "HubSpaceDataUpdateCoordinator", autospec=True
    )
    coord_mock.conn = mocked_hubspace
    coord_mock.data = defaultdict(dict)
    yield coord_mock


@pytest.fixture
def mocked_hubspace(mocker):
    """Mock all HubSpace functionality but ensure the class is correct"""
    hs_mock = mocker.patch.object(hubspace_async, "HubSpaceConnection", autospec=True)
    yield hs_mock


@pytest.fixture(autouse=True)
def set_debug_mode(caplog):
    # Force capture of all debug logging. This is useful if you want to verify
    # log messages with `<message> in caplog.text`. If you run
    # pytest -rP it will display all log messages, including passing tests.
    caplog.set_level(logging.DEBUG)
