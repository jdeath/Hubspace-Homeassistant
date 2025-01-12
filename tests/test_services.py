import pytest
from aiohubspace.v1.device import HubspaceState

from custom_components.hubspace import const, services

from .utils import create_devices_from_data, modify_state

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]
fan_zandra_light_id = "light.friendly_device_2_light"


@pytest.fixture
async def mocked_entity(mocked_entry):
    hass, entry, bridge = mocked_entry
    await bridge.lights.initialize_elem(fan_zandra_light)
    await bridge.devices.initialize_elem(fan_zandra[2])
    bridge.add_device(fan_zandra_light.id, bridge.lights)
    bridge.add_device(fan_zandra[2].id, bridge.devices)
    bridge.lights._initialized = True
    bridge.devices._initialized = True
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "account, entity_id, error_entity, error_bridge",
    [
        # Use any bridge
        (
            None,
            fan_zandra_light_id,
            None,
            None,
        ),
        # Use bridge that has an account match
        ("username", fan_zandra_light_id, None, None),
        # Invalid entity
        ("username", "i dont exist", True, None),
        # No bridge that uses username
        ("username2", fan_zandra_light_id, None, True),
    ],
)
async def test_service_valid_no_username(
    account, entity_id, error_entity, error_bridge, mocked_entity, caplog
):
    hass, entry, bridge = mocked_entity
    assert hass.states.get(fan_zandra_light_id).state == "on"
    await hass.services.async_call(
        const.DOMAIN,
        services.SERVICE_SEND_COMMAND,
        service_data={
            "entity_id": [entity_id],
            "value": "off",
            "functionClass": "power",
            "functionInstance": "light-power",
            "account": account,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    if not error_entity and not error_bridge:
        update_call = bridge.request.call_args_list[-1]
        assert update_call.args[0] == "put"
        payload = update_call.kwargs["json"]
        assert payload["metadeviceId"] == fan_zandra_light.id
        assert payload["values"] == [
            {
                "functionClass": "power",
                "functionInstance": "light-power",
                "value": "off",
            }
        ]
        # Now generate update event by emitting the json we've sent as incoming event
        light_update = create_devices_from_data("fan-ZandraFan.json")[1]
        modify_state(
            light_update,
            HubspaceState(
                functionClass="power",
                functionInstance="light-power",
                value="off",
            ),
        )
        event = {
            "type": "update",
            "device_id": light_update.id,
            "device": light_update,
            "force_forward": True,
        }
        bridge.emit_event("update", event)
        await hass.async_block_till_done()
        assert hass.states.get(fan_zandra_light_id).state == "off"
    else:
        bridge.request.assert_not_called()
        if error_entity:
            assert f"Entity {entity_id} not found" in caplog.text
        if error_bridge:
            assert f"No bridge using account {account}" in caplog.text
