"""Hatch metadata hook: version and dependencies from the integration manifest."""

from __future__ import annotations

import json
from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface

MANIFEST_PATH = (
    Path(__file__).resolve().parent / "custom_components/hubspace/manifest.json"
)


def load_manifest() -> dict:
    """Load Home Assistant integration manifest."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


class HubspaceManifestMetadataHook(MetadataHookInterface):
    """Populate project version and dependencies from manifest.json."""

    def update(self, metadata: dict) -> None:
        """Set version and dependencies from the integration manifest."""
        manifest = load_manifest()
        metadata["version"] = manifest["version"]
        metadata["dependencies"] = list(manifest["requirements"])
