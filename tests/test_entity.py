"""Tests for HubspaceBaseEntity naming."""

from unittest.mock import MagicMock

from aioafero.device import SplitDeviceId

from custom_components.hubspace.entity import HubspaceBaseEntity


def _mock_resource(*, split: SplitDeviceId | None = None, name: str = "Device"):
    resource = MagicMock()
    resource.id = (
        str(split) if split is not None else "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    resource.type.value = "light"
    resource.split = split
    resource.instance = None if split is None else split.instance
    resource.device_information.name = name
    resource.device_information.parent_id = (
        split.parent_id if split is not None else resource.id
    )
    return resource


def test_split_entity_name_uses_instance_not_rsplit():
    """Instances containing the split token must not be parsed from the id."""
    bridge = MagicMock()
    bridge.logger.getChild.return_value = MagicMock()
    split = SplitDeviceId(
        parent_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        identifier="light",
        instance="light-sensor-enabled",
    )
    entity = HubspaceBaseEntity(bridge, MagicMock(), _mock_resource(split=split))
    assert entity._attr_name == "light-sensor-enabled"  # noqa: SLF001


def test_unsplit_entity_has_no_name_override():
    """Primary entities rely on device name via has_entity_name."""
    bridge = MagicMock()
    bridge.logger.getChild.return_value = MagicMock()
    entity = HubspaceBaseEntity(bridge, MagicMock(), _mock_resource())
    assert entity._attr_name is None  # noqa: SLF001
