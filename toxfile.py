"""Register HA tox envs from hacs.json (same logic as CI matrix-prep).

See docs/testing.md. Requires tox >= 4.29.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
import sys
from typing import cast

from tox.config.loader.memory import MemoryLoader
from tox.config.types import EnvList
from tox.plugin import impl

_ROOT = Path(__file__).resolve().parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from phcc_matrix import (  # noqa: E402
    TOX_PYTHON_TAG_RE,
    list_tox_envs,
    parse_ha_month_from_env,
    tox_env_to_python_version,
)
from tox_ha_install import load_manifest_requirements  # noqa: E402


def _cli_selections() -> list[str]:
    """Tox env names passed via -e / --env on the command line."""
    args = sys.argv[1:]
    selections: list[str] = []

    for i, arg in enumerate(args):
        if arg in {"-e", "--env"}:
            if i + 1 < len(args):
                selections.extend(args[i + 1].split(","))
            continue
        if arg.startswith("--env="):
            selections.extend(arg.split("=", 1)[1].split(","))

    return [part for part in selections if part]


def _lint_only_cli() -> bool:
    """Return whether tox was invoked with only ``-e lint`` (skip phcc index)."""
    selections = _cli_selections()
    return bool(selections) and all(part == "lint" for part in selections)


def _explicit_ha_envs_cli() -> tuple[str, ...] | None:
    """HA env names from -e when set; None means discover full matrix (tox -av / run-parallel)."""
    selections = _cli_selections()
    if not selections:
        return None
    ha_envs = [part for part in selections if part != "lint"]
    if not ha_envs:
        return None
    if not all(TOX_PYTHON_TAG_RE.match(part) for part in ha_envs):
        return None
    return tuple(ha_envs)


@functools.lru_cache
def _manifest_requirements() -> tuple[str, ...]:
    return tuple(load_manifest_requirements())


def _phcc_index_setenv() -> dict[str, str]:
    """Use the on-disk phcc index without PyPI when it already exists (faster local/CI runs)."""
    index_path = _ROOT / ".tox" / "phcc_version_index.json"
    if index_path.is_file():
        return {"PHCC_INDEX_OFFLINE": "1"}
    return {}


def _apply_phcc_offline_if_index_present() -> None:
    """Enable offline mode in the tox parent process (setenv does not apply during discovery)."""
    if "PHCC_INDEX_OFFLINE" not in os.environ:
        os.environ.update(_phcc_index_setenv())


@functools.lru_cache
def _ha_tox_envs() -> tuple[str, ...]:
    _apply_phcc_offline_if_index_present()
    return tuple(list_tox_envs())


@impl
def tox_add_core_config(core_conf, state):
    """Append HA envs to envlist so run-parallel picks them up (not only tox -e)."""
    if _lint_only_cli():
        return
    _apply_phcc_offline_if_index_present()
    explicit = _explicit_ha_envs_cli()
    names = explicit if explicit is not None else _ha_tox_envs()
    env_list = cast(EnvList, core_conf["env_list"])
    for name in names:
        if name not in env_list.envs:
            env_list.envs.append(name)


@impl
def tox_add_env_config(env_conf, state):
    """Set a human-readable description for each HA month env."""
    name = env_conf.env_name
    if name == "lint" or not TOX_PYTHON_TAG_RE.match(name):
        return
    ha_month = parse_ha_month_from_env(name)
    if ha_month is None:
        return
    python_version = tox_env_to_python_version(name)
    manifest_deps = list(_manifest_requirements())
    env_conf.loaders.insert(
        0,
        MemoryLoader(
            description=f"Integration tests on Home Assistant {ha_month} (Python {python_version})",
            # Full deps list (MemoryLoader overrides tox.ini deps); keep test + manifest pins.
            deps=["-rtest-requirements.txt", *manifest_deps],
            setenv={
                "HUBSPACE_MANIFEST_REQUIREMENTS": "\n".join(manifest_deps),
                **_phcc_index_setenv(),
            },
        ),
    )
