import contextlib
import os
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.hubspace import button

EXPECTED_DIR = os.path.dirname(os.path.realpath(button.__file__))

gen_debug = "button.hubspace_api_username_generate_debug"
gen_raw = "button.hubspace_api_username_generate_raw"


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entry):
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_reg = er.async_get(hass)
    assert entity_reg.async_get(gen_debug) is not None
    assert entity_reg.async_get(gen_raw) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entity_id,expected_file",
    [(gen_debug, "_dump_hs_devices.json"), (gen_raw, "_dump_raw.json")],
)
async def test_press_button(entity_id, expected_file, mocked_entry, mocker):
    hass, entry, bridge = mocked_entry
    mocker.patch.object(bridge, "fetch_data", side_effect=AsyncMock(return_value=[]))
    expected_path = os.path.join(EXPECTED_DIR, expected_file)
    with contextlib.suppress(Exception):
        os.unlink(expected_path)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id},
        blocking=True,
    )
    try:
        assert os.path.isfile(expected_path)
    except AssertionError:
        raise
    finally:
        with contextlib.suppress(Exception):
            os.unlink(expected_path)
