"""Register HA tox envs from hacs.json (same logic as CI matrix-prep).

See docs/testing.md. Requires tox >= 4.29.
"""

from __future__ import annotations

import functools
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
    if not selections or any(part == "lint" for part in selections):
        return None
    if not all(TOX_PYTHON_TAG_RE.match(part) for part in selections):
        return None
    return tuple(selections)


@functools.lru_cache
def _ha_tox_envs() -> tuple[str, ...]:
    return tuple(list_tox_envs())


@impl
def tox_add_core_config(core_conf, state):
    """Append HA envs to envlist so run-parallel picks them up (not only tox -e)."""
    if _lint_only_cli():
        return
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
    env_conf.loaders.insert(
        0,
        MemoryLoader(
            description=f"Integration tests on Home Assistant {ha_month} (Python {python_version})"
        ),
    )
