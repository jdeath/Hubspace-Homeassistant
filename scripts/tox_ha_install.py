#!/usr/bin/env python3
"""Tox install_command: install deps + phcc for the HA month implied by {envname}."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
import sys

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
MANIFEST_PATH = _ROOT / "custom_components" / "hubspace" / "manifest.json"
LOCAL_AIOAFERO = (_ROOT / ".." / "aioafero").resolve()

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from phcc_matrix import get_month_spec, parse_ha_month_from_env  # noqa: E402

logger = logging.getLogger("tox_ha_install")


def _rewrite_local_aioafero(requirements: list[str]) -> list[str]:
    """Prefer editable ../aioafero when developing against an unreleased version."""
    if not (LOCAL_AIOAFERO / "pyproject.toml").is_file():
        return requirements
    rewritten: list[str] = []
    for req in requirements:
        name = req.split("@", 1)[0].strip() if "@" in req else req
        if name == "aioafero" or req.startswith("aioafero=="):
            # One tox dep line (bare ``-e`` alone crashes PythonDeps). Tox splits
            # ``-e /path`` when expanding {packages}; pip still needs two argv
            # tokens — see ``_pip_argv``.
            rewritten.append(f"-e {LOCAL_AIOAFERO}")
        else:
            rewritten.append(req)
    return rewritten


def _pip_argv(requirements: list[str]) -> list[str]:
    r"""Expand ``-e /path`` lines into separate argv tokens for pip.

    A single ``"-e /path"`` argument is rejected by pip as an invalid editable
    requirement; ``-e`` and ``/path`` must be consecutive argv entries.
    """
    argv: list[str] = []
    for req in requirements:
        if req.startswith("-e "):
            path = req[3:].strip()
            if not path:
                raise ValueError(f"editable requirement missing path: {req!r}")
            argv.extend(["-e", path])
        else:
            argv.append(req)
    return argv


def load_manifest_requirements() -> list[str]:
    """Integration runtime deps from manifest.json (same source HACS uses)."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    requirements = data.get("requirements")
    if not requirements:
        raise KeyError(f"{MANIFEST_PATH} missing 'requirements'")
    return _rewrite_local_aioafero(list(requirements))


def main() -> int:
    """Tox install_command entry point."""
    # tox 4: install_command = python .../tox_ha_install.py {envname} {opts} {packages}
    argv = sys.argv[1:]
    if not argv:
        logger.error("usage: tox_ha_install.py <envname> [pip opts and packages...]")
        return 2

    env_name = argv[0]
    pip_args = argv[1:]

    ha_month = parse_ha_month_from_env(env_name)
    if ha_month is None or "--no-deps" in pip_args:
        cmd = [sys.executable, "-I", "-m", "pip", "install", *pip_args]
        return subprocess.call(cmd)

    spec = get_month_spec(ha_month)
    packages = _pip_argv(
        [
            *load_manifest_requirements(),
            spec.phcc_spec,
            *([spec.pycares_constraint] if spec.pycares_constraint else []),
        ]
    )

    cmd = [
        sys.executable,
        "-I",
        "-m",
        "pip",
        "install",
        *pip_args,
        *packages,
    ]
    logger.info("%s -> HA %s (%s)", env_name, ha_month, spec.homeassistant)
    logger.info("%s", spec.phcc_spec)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
