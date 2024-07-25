import pytest

from custom_components.hubspace import lock
from custom_components.hubspace.const import ENTITY_LOCK

from .utils import create_devices_from_data

lock_tbd = create_devices_from_data("door-lock-TBD.json")
lock_tbd_instance = lock_tbd[0]


@pytest.fixture
def empty_lock(mocked_coordinator):
    yield lock.HubSpaceLock(mocked_coordinator, "test lock")


@pytest.mark.parametrize(
    "states, expected_attrs, extra_attrs",
    [
        (
            lock_tbd_instance.states,
            {
                "_current_position": "right",
            },
            {
                "Child ID": None,
                "deviceId": None,
                "model": None,
            },
        )
    ],
)
def test_update_states(states, expected_attrs, extra_attrs, empty_lock):
    empty_lock.states = states
    empty_lock.coordinator.data[ENTITY_LOCK][empty_lock._child_id] = empty_lock
    empty_lock.update_states()
    assert empty_lock.extra_state_attributes == extra_attrs
    for key, val in expected_attrs.items():
        assert getattr(empty_lock, key) == val


def test_name(empty_lock):
    assert empty_lock.name == "test lock"


def test_unique_id(empty_lock):
    empty_lock._child_id = "beans"
    assert empty_lock.unique_id == "beans"


def test_extra_state_attributes(mocked_coordinator):
    model = "bean model"
    device_id = "bean-123"
    child_id = "bean-123-123"
    test_fan = lock.HubSpaceLock(
        mocked_coordinator,
        "test lock",
        model=model,
        device_id=device_id,
        child_id=child_id,
    )
    assert test_fan.extra_state_attributes == {
        "model": model,
        "deviceId": device_id,
        "Child ID": child_id,
    }


@pytest.mark.asyncio
async def test_async_lock(empty_lock):
    await empty_lock.async_lock()
    assert empty_lock._current_position == "right"


@pytest.mark.asyncio
async def test_async_unlock(empty_lock):
    await empty_lock.async_unlock()
    assert empty_lock._current_position == "left"
