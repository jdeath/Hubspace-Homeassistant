import pytest
from homeassistant.helpers import entity_registry as er

from .utils import create_devices_from_data

lock_tbd = create_devices_from_data("door-lock-TBD.json")
lock_tbd_instance = lock_tbd[0]
lock_id = "lock.friendly_device_0_lock"


@pytest.fixture
async def transformer_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.locks.initialize_elem(lock_tbd_instance)
    await bridge.devices.initialize_elem(lock_tbd_instance)
    bridge.locks._initialize = True
    bridge.devices._initialize = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev,expected_entities",
    [
        (
            lock_tbd_instance,
            [lock_id],
        ),
    ],
)
async def test_async_setup_entry(dev, expected_entities, mocked_entry):
    try:
        hass, entry, bridge = mocked_entry
        await bridge.locks.initialize_elem(dev)
        await bridge.devices.initialize_elem(dev)
        bridge.locks._initialize = True
        bridge.devices._initialize = True
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_reg = er.async_get(hass)
        for entity in expected_entities:
            assert entity_reg.async_get(entity) is not None
    finally:
        await bridge.close()


@pytest.mark.asyncio
async def test_unlock(transformer_entity):
    hass, entry, bridge = transformer_entity
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": lock_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == lock_tbd_instance.id


@pytest.mark.asyncio
async def test_lock(transformer_entity):
    hass, entry, bridge = transformer_entity
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": lock_id},
        blocking=True,
    )
    update_call = bridge.request.call_args_list[-1]
    assert update_call.args[0] == "put"
    payload = update_call.kwargs["json"]
    assert payload["metadeviceId"] == lock_tbd_instance.id
