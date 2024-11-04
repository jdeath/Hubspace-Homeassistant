import pytest
from hubspace_async import HubSpaceDevice

from custom_components.hubspace import switch
from custom_components.hubspace.const import ENTITY_SWITCH

from .utils import create_devices_from_data

dummy_device = HubSpaceDevice(
    "child_id",
    "device_id",
    "test_model",
    "switch",
    "device_name",
    "friendly_image",
    "test switch",
    functions=[],
    states=[],
    children=[],
)


@pytest.fixture
def single_switch(mocked_coordinator):
    yield switch.HubSpaceSwitch(mocked_coordinator, dummy_device, instance=None)


transformer = create_devices_from_data("transformer.json")[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "instance,states,expected_attrs",
    [
        ("zone-1", transformer.states, {"_state": "off", "_availability": True}),
        ("zone-2", transformer.states, {"_state": "on", "_availability": True}),
    ],
)
async def test_update_states(instance, states, expected_attrs, single_switch):
    single_switch._instance = instance
    single_switch.states = states
    single_switch.coordinator.data[ENTITY_SWITCH][single_switch._child_id] = {
        "device": single_switch
    }
    single_switch.update_states()
    for key, val in expected_attrs.items():
        assert getattr(single_switch, key) == val


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_instances",
    [
        (transformer, ["zone-2", "zone-3", "zone-1"]),
    ],
)
async def test_setup_entry_toggled(dev, expected_instances, mocked_coordinator):
    res = await switch.setup_entry_toggled(mocked_coordinator, dev)
    assert len(res) == len(expected_instances)
    for ind, entity in enumerate(res):
        assert entity._instance == expected_instances[ind]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "devs,expected_instances",
    [
        ({transformer.id: transformer}, ["zone-2", "zone-3", "zone-1"]),
    ],
)
async def test_async_setup_entry(devs, expected_instances, mocked_coordinator, mocker):
    mocker.patch.object(switch, "dr")
    hass = mocker.Mock()
    add_entities = mocker.Mock()
    entry = mocker.Mock()
    entry.runtime_data.coordinator_hubspace = mocked_coordinator
    mocked_coordinator.data[ENTITY_SWITCH] = devs
    await switch.async_setup_entry(hass, entry, add_entities)
    added_devs = add_entities.call_args_list[0][0]
    for ind, dev in enumerate(added_devs):
        assert dev[0]._instance == expected_instances[ind]
