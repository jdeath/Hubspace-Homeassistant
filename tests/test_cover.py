"""Test the integration between Home Assistant Covers and Afero blinds."""

from aioafero import AferoState, EventType
from aioafero.v1.controllers.base import BaseResourcesController
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    CoverEntityFeature,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers import entity_registry as er
import pytest

from .utils import create_devices_from_data, modify_state

gateway = create_devices_from_data("blinds-gateway.json")[0]
blinds = create_devices_from_data("blinds-zone.json")[0]
blinds_id = "cover.smart_blinds_gateway_office_blinds"


@pytest.fixture
async def mocked_entity(mocked_entry):
    """Initialize a mocked blinds zone and register it within Home Assistant."""
    hass, entry, bridge = mocked_entry
    await bridge.generate_devices_from_data([gateway, blinds])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass, entry, bridge
    await bridge.close()


async def _call(hass, bridge, service, data=None):
    await hass.services.async_call(
        COVER_DOMAIN,
        service,
        {ATTR_ENTITY_ID: blinds_id, **(data or {})},
        blocking=True,
    )
    await bridge.async_block_until_done()
    await hass.async_block_till_done()
    return hass.states.get(blinds_id)


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entity):
    """Ensure blinds are discovered with their position and features."""
    hass, _, _ = mocked_entity
    assert er.async_get(hass).async_get(blinds_id) is not None
    entity = hass.states.get(blinds_id)
    assert entity.state == STATE_OPEN
    assert entity.attributes[ATTR_DEVICE_CLASS] == "blind"
    assert entity.attributes[ATTR_CURRENT_POSITION] == 100
    assert entity.attributes[ATTR_SUPPORTED_FEATURES] == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )


@pytest.mark.asyncio
async def test_close_open(mocked_entity):
    """Ensure close / open round-trip through the controller."""
    hass, _, bridge = mocked_entity
    entity = await _call(hass, bridge, SERVICE_CLOSE_COVER)
    assert entity.state == STATE_CLOSED
    assert bridge.blinds[blinds.id].position.position == 0
    entity = await _call(hass, bridge, SERVICE_OPEN_COVER)
    assert entity.state == STATE_OPEN
    assert bridge.blinds[blinds.id].position.position == 100


@pytest.mark.asyncio
@pytest.mark.parametrize(("requested", "expected"), [(50, 50), (60, 50), (90, 100)])
async def test_set_position(mocked_entity, requested, expected):
    """Ensure positions are snapped to the step the device advertises."""
    hass, _, bridge = mocked_entity
    entity = await _call(
        hass, bridge, SERVICE_SET_COVER_POSITION, {ATTR_POSITION: requested}
    )
    assert entity.attributes[ATTR_CURRENT_POSITION] == expected
    assert bridge.blinds[blinds.id].position.position == expected


@pytest.mark.asyncio
async def test_stop(mocked_entity):
    """Ensure stop sends the stop command to the cloud."""
    hass, _, bridge = mocked_entity
    stop_state = {"functionClass": "stop-moving", "functionInstance": None}
    bridge.mock_update_afero_api(blinds.id, [{**stop_state, "value": "stop"}])
    await _call(hass, bridge, SERVICE_STOP_COVER)
    sent = BaseResourcesController.update_afero_api.call_args.args
    assert sent[0] == blinds.id
    assert [
        (state["functionClass"], state["functionInstance"], state["value"])
        for state in sent[1]
    ] == [("stop-moving", None, "stop")]


@pytest.mark.asyncio
async def test_missing_features(mocked_entity):
    """A zone without a position or stop command degrades instead of crashing."""
    hass, _, bridge = mocked_entity
    resource = bridge.blinds[blinds.id]
    resource.position = None
    resource.commands = {}
    await bridge.blinds.emit_to_subscribers(
        EventType.RESOURCE_UPDATED, blinds.id, resource
    )
    await hass.async_block_till_done()
    entity = hass.states.get(blinds_id)
    assert ATTR_CURRENT_POSITION not in entity.attributes
    assert entity.attributes[ATTR_SUPPORTED_FEATURES] == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    )


def _gateway_update(available: bool):
    update = create_devices_from_data("blinds-gateway.json")[0]
    modify_state(
        update,
        AferoState(functionClass="available", functionInstance=None, value=available),
    )
    return update


@pytest.mark.asyncio
async def test_unavailable_with_gateway(mocked_entity):
    """A zone follows its gateway, even though the zone reports itself available."""
    hass, _, bridge = mocked_entity
    assert hass.states.get(blinds_id).state == STATE_OPEN
    # A discovery poll where only the gateway went offline
    await bridge.generate_devices_from_data([_gateway_update(False), blinds])
    await hass.async_block_till_done()
    assert hass.states.get(blinds_id).state == STATE_UNAVAILABLE
    # And back once the gateway returns
    await bridge.generate_devices_from_data([_gateway_update(True), blinds])
    await hass.async_block_till_done()
    assert hass.states.get(blinds_id).state == STATE_OPEN


@pytest.mark.asyncio
async def test_add_new_device(mocked_entry):
    """Ensure blinds discovered after setup are added."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(blinds_id) is None
    await bridge.generate_devices_from_data([gateway, blinds])
    await hass.async_block_till_done()
    assert hass.states.get(blinds_id).state == STATE_OPEN


@pytest.mark.asyncio
async def test_zone_name_is_stripped(mocked_entry):
    """Stray whitespace in the zone name does not leak into the entity name."""
    hass, entry, bridge = mocked_entry
    padded = create_devices_from_data("blinds-zone.json")[0]
    padded.friendly_name = f"  {padded.friendly_name} "
    await bridge.generate_devices_from_data([gateway, padded])
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get(blinds_id).original_name == "Office Blinds"
