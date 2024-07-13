import pytest

from custom_components.hubspace import hubspace


@pytest.fixture
def mocked_hubspace(mocker):
    """Mock all HubSpace functionality but ensure the class is correct"""
    hs_mock = mocker.patch.object(hubspace, "HubSpace", autospec=True)
    return hs_mock
