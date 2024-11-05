import pytest
from hubspace_async import HubSpaceDevice

from custom_components.hubspace import valve
from custom_components.hubspace.const import ENTITY_VALVE

from .utils import create_devices_from_data

dummy_device = HubSpaceDevice(
    "child_id",
    "device_id",
    "test_model",
    "valve",
    "device_name",
    "friendly_image",
    "test valve",
    functions=[],
    states=[],
    children=[],
)


@pytest.fixture
def empty_valve(mocked_coordinator):
    yield valve.HubSpaceValve(mocked_coordinator, dummy_device, instance=None)


spigot = create_devices_from_data("water-timer.json")[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "instance,states,expected_attrs",
    [
        ("spigot-1", spigot.states, {"_state": "off", "_availability": True}),
        ("spigot-2", spigot.states, {"_state": "on", "_availability": True}),
    ],
)
async def test_update_states(instance, states, expected_attrs, empty_valve):
    empty_valve._instance = instance
    empty_valve.states = states
    empty_valve.coordinator.data[ENTITY_VALVE][empty_valve._child_id] = {
        "device": empty_valve
    }
    empty_valve.update_states()
    for key, val in expected_attrs.items():
        assert getattr(empty_valve, key) == val
