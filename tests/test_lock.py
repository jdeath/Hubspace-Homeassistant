import pytest
from hubspace_async import HubSpaceDevice

from custom_components.hubspace import lock
from custom_components.hubspace.const import ENTITY_LOCK

from .utils import create_devices_from_data

lock_tbd = create_devices_from_data("door-lock-TBD.json")
lock_tbd_instance = lock_tbd[0]

dummy_device = HubSpaceDevice(
    "child_id",
    "device_id",
    "test_model",
    "light",
    "device_name",
    "friendly_image",
    "test lock",
    functions=[],
    states=[],
    children=[],
)


@pytest.fixture
def empty_lock(mocked_coordinator):
    yield lock.HubSpaceLock(mocked_coordinator, dummy_device)


@pytest.mark.parametrize(
    "states, expected_attrs",
    [
        (
            lock_tbd_instance.states,
            {
                "_current_position": "locked",
                "_availability": True,
            },
        )
    ],
)
def test_update_states(states, expected_attrs, empty_lock):
    empty_lock.states = states
    empty_lock.coordinator.data[ENTITY_LOCK][empty_lock._child_id] = {
        "device": empty_lock
    }
    empty_lock.update_states()
    for key, val in expected_attrs.items():
        assert getattr(empty_lock, key) == val


def test_name(empty_lock):
    assert empty_lock.name == "test lock"


def test_unique_id(empty_lock):
    empty_lock._device.id = "beans"
    assert empty_lock.unique_id == "beans"


@pytest.mark.asyncio
async def test_async_lock(empty_lock):
    await empty_lock.async_lock()
    assert empty_lock._current_position == "locking"


@pytest.mark.asyncio
async def test_async_unlock(empty_lock):
    await empty_lock.async_unlock()
    assert empty_lock._current_position == "unlocking"
