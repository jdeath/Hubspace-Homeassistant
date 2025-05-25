"""Test the integration for buttons correctly creates the debug files."""

import contextlib
import os
from pathlib import Path
from unittest.mock import AsyncMock

from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.hubspace import button

EXPECTED_DIR: Path = Path(button.__file__.rsplit(os.sep, 1)[0])

gen_debug = "button.hubspace_api_username_generate_debug"
gen_raw = "button.hubspace_api_username_generate_raw"


@pytest.mark.asyncio
async def test_async_setup_entry(mocked_entry):
    """Ensure the two debug buttons are present."""
    hass, entry, bridge = mocked_entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_reg = er.async_get(hass)
    assert entity_reg.async_get(gen_debug) is not None
    assert entity_reg.async_get(gen_raw) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "entity_id",
        "expected_file",
    ),
    [(gen_debug, "_dump_hs_devices.json"), (gen_raw, "_dump_raw.json")],
)
async def test_press_button(entity_id, expected_file, mocked_entry, mocker):
    """Ensure the file is created when the button is pressed."""
    hass, entry, bridge = mocked_entry
    mocker.patch.object(bridge, "fetch_data", side_effect=AsyncMock(return_value=[]))
    expected_path = EXPECTED_DIR / expected_file
    with contextlib.suppress(Exception):
        Path(expected_path).unlink()
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id},
        blocking=True,
    )
    try:
        assert Path(expected_path).exists()
    except AssertionError:  # noqa: TRY203
        # This should be ignored as we want the test directory
        # to be cleaned up after the test
        raise
    finally:
        with contextlib.suppress(Exception):
            Path(expected_path).unlink()
