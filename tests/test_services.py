"""Test the integration between Home Assistant Services and Afero devices."""

from aioafero import AferoState
import pytest
import voluptuous as vol

from custom_components.hubspace import const, services

from .utils import create_devices_from_data, hs_raw_from_dump, modify_state

fan_zandra = create_devices_from_data("fan-ZandraFan.json")
fan_zandra_light = fan_zandra[1]
fan_zandra_light_id = "light.friendly_device_2_light"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked Fan and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    # Register callbacks
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Now generate update event by emitting the json we've sent as incoming event
    afero_data = hs_raw_from_dump("fan-ZandraFan.json")
    await bridge.generate_events_from_data(afero_data)
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    assert len(bridge.devices.items) == 1
    yield hass, entry, bridge
    await bridge.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "account",
        "entity_id",
        "error_entity",
        "error_bridge",
    ),
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
    """Ensure the correct states are sent and the entity is properly updated."""
    hass, _, bridge = mocked_entity
    assert hass.states.get(fan_zandra_light_id).state == "on"
    if not error_entity and not error_bridge:
        await hass.services.async_call(
            const.DOMAIN,
            services.SERVICE_SEND_COMMAND,
            service_data={
                "entity_id": [entity_id],
                "value": "off",
                "function_class": "power",
                "function_instance": "light-power",
                "account": account,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
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
            AferoState(
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
            with pytest.raises(vol.error.MultipleInvalid):
                await hass.services.async_call(
                    const.DOMAIN,
                    services.SERVICE_SEND_COMMAND,
                    service_data={
                        "entity_id": [entity_id],
                        "value": "off",
                        "function_class": "power",
                        "function_instance": "light-power",
                        "account": account,
                    },
                    blocking=True,
                )
            await hass.async_block_till_done()
        else:
            await hass.services.async_call(
                const.DOMAIN,
                services.SERVICE_SEND_COMMAND,
                service_data={
                    "entity_id": [entity_id],
                    "value": "off",
                    "function_class": "power",
                    "function_instance": "light-power",
                    "account": account,
                },
                blocking=True,
            )
            await hass.async_block_till_done()
            if error_bridge:
                assert f"No bridge using account {account}" in caplog.text
