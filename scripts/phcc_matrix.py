"""Resolve pytest-homeassistant-custom-component (phcc) pins per Home Assistant month.

phcc releases pin homeassistant==X.Y.Z. Tox env factors like ha202603 map to HA month
2026.3. An on-disk version index is updated incrementally from PyPI (only new phcc
releases are fetched). No manual --refresh unless you want to force a full rescan.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import TypedDict
import urllib.request

logger = logging.getLogger("phcc_matrix")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(message)s",
        stream=sys.stderr,
    )

PHCC_PROJECT = "pytest-homeassistant-custom-component"
PHCC_PYPI_JSON = f"https://pypi.org/pypi/{PHCC_PROJECT}/json"
HA_PYPI_JSON = "https://pypi.org/pypi/homeassistant/json"
HA_FACTOR_RE = re.compile(r"ha(\d{4,6})")
TOX_PYTHON_TAG_RE = re.compile(r"^(py\d+)-")
PHCC_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
HA_RELEASE_RE = re.compile(r"^(20\d{2})\.(\d+)\.\d+$")
REQUIRES_PYTHON_MIN_RE = re.compile(r">=(\d+)\.(\d+)")

ROOT = Path(__file__).resolve().parents[1]
HACS_PATH = ROOT / "hacs.json"
INDEX_PATH = Path(
    os.environ.get("PHCC_INDEX_PATH", ROOT / ".tox" / "phcc_version_index.json")
)


def _index_offline_mode() -> bool:
    """When set (e.g. CI matrix jobs), use the on-disk index only — no PyPI refresh."""
    return os.environ.get("PHCC_INDEX_OFFLINE", "").lower() in {"1", "true", "yes"}


class VersionIndex(TypedDict):
    """On-disk phcc index payload."""

    versions: dict[str, str]
    ha_python_requires: dict[str, str]


def _out(message: str) -> None:
    """Write a line to stdout."""
    sys.stdout.write(f"{message}\n")


def _fetch_json(url: str, *, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _fetch_optional_json(url: str, *, timeout: int) -> dict | None:
    try:
        return _fetch_json(url, timeout=timeout)
    except OSError:
        return None


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _ha_version_key(version: str) -> tuple[int, ...]:
    """Sort key for homeassistant calver (stable releases only for comparisons)."""
    parts = version.split(".")
    patch = parts[2] if len(parts) > 2 else "0"
    if "b" in patch:
        patch = patch.split("b", 1)[0] or "0"
    return (int(parts[0]), int(parts[1]), int(patch))


@dataclass(frozen=True)
class MonthSpec:
    """Resolved phcc install pin for one Home Assistant month."""

    ha_month: str
    phcc_spec: str
    pycares_pin: bool
    homeassistant: str


def load_hacs_min_ha_month() -> str:
    """Minimum HA version from hacs.json (integration support floor)."""
    data = json.loads(HACS_PATH.read_text(encoding="utf-8"))
    ha = data.get("homeassistant")
    if not ha:
        raise KeyError(f"{HACS_PATH} missing 'homeassistant'")
    return ha


def _month_key(ha_month: str) -> tuple[int, int]:
    year, month = ha_month.split(".", 1)
    return int(year), int(month)


def fetch_latest_ha_month_from_pypi() -> str:
    """Latest Home Assistant release month from PyPI (e.g. 2026.5)."""
    project = _fetch_json(HA_PYPI_JSON, timeout=60)
    latest_key: tuple[int, int] | None = None
    latest_month: str | None = None
    for version in project.get("releases", {}):
        if "b" in version:
            continue
        match = HA_RELEASE_RE.match(version)
        if not match:
            continue
        key = int(match.group(1)), int(match.group(2))
        if latest_key is None or key > latest_key:
            latest_key = key
            latest_month = f"{key[0]}.{key[1]}"
    if latest_month is None:
        raise LookupError("No homeassistant calver releases found on PyPI")
    return latest_month


def resolve_max_ha_month(versions: dict[str, str] | None = None) -> str:
    """Upper HA month from latest PyPI homeassistant release."""
    if not _index_offline_mode():
        try:
            return fetch_latest_ha_month_from_pypi()
        except OSError as err:
            logger.warning("PyPI homeassistant lookup failed: %s", err)
    if versions:
        available = sorted({_ha_minor(v) for v in versions.values()}, key=_month_key)
        if available:
            logger.info(
                "using latest phcc-index month %s as max", available[-1]
            )
            return available[-1]
    raise LookupError(
        "Could not determine latest Home Assistant month (PyPI unreachable and no phcc index)"
    )


def iter_ha_months(min_month: str, max_month: str) -> Iterator[str]:
    """Yield HA months from min_month through max_month inclusive."""
    year, month = _month_key(min_month)
    y2, m2 = _month_key(max_month)
    while (year, month) <= (y2, m2):
        yield f"{year}.{month}"
        month += 1
        if month > 12:
            year += 1
            month = 1


def ha_month_to_factor(ha_month: str) -> str:
    """Tox ha factor suffix (e.g. 2025.7 -> 20257, 2026.3 -> 202603)."""
    year, month = _month_key(ha_month)
    if year >= 2026 and month < 10:
        return f"{year}{month:02d}"
    return f"{year}{month}"


def _fetch_ha_python_requires(homeassistant_version: str) -> str | None:
    """Requires-Python from PyPI for a homeassistant release (e.g. '>=3.14.0')."""
    url = f"https://pypi.org/pypi/homeassistant/{homeassistant_version}/json"
    project = _fetch_optional_json(url, timeout=30)
    if project is None:
        return None
    return project.get("info", {}).get("requires_python")


def _min_python_from_requires_python(requires_python: str) -> tuple[int, int]:
    """Lower bound (major, minor) from a Requires-Python string."""
    match = REQUIRES_PYTHON_MIN_RE.search(requires_python)
    if not match:
        raise ValueError(f"Cannot parse Requires-Python: {requires_python!r}")
    return int(match.group(1)), int(match.group(2))


def _latest_ha_version_for_month(ha_month: str, versions: dict[str, str]) -> str:
    candidates = [ha for ha in versions.values() if _ha_minor(ha) == ha_month]
    if not candidates:
        raise LookupError(f"No homeassistant version indexed for HA month {ha_month}")
    stable = [ha for ha in candidates if "b" not in ha]
    return max(stable or candidates, key=_ha_version_key)


def _python_tag_for_ha_month(
    ha_month: str,
    versions: dict[str, str],
    ha_python_requires: dict[str, str],
) -> str:
    """Tox Python factor (py313, py314, …) from homeassistant Requires-Python on PyPI."""
    ha_version = _latest_ha_version_for_month(ha_month, versions)
    requires = ha_python_requires.get(ha_version)
    if not requires:
        requires = _fetch_ha_python_requires(ha_version)
        if requires:
            ha_python_requires[ha_version] = requires
    if not requires:
        raise LookupError(
            f"No Requires-Python metadata for homeassistant=={ha_version} on PyPI"
        )
    major, minor = _min_python_from_requires_python(requires)
    return f"py{major}{minor}"


def ha_month_to_tox_env(
    ha_month: str,
    versions: dict[str, str],
    ha_python_requires: dict[str, str],
) -> str:
    """Map an HA month to a tox environment name (e.g. 2026.3 -> py314-ha202603)."""
    py_tag = _python_tag_for_ha_month(ha_month, versions, ha_python_requires)
    return f"{py_tag}-ha{ha_month_to_factor(ha_month)}"


def _python_tag_to_version(py_tag: str) -> str:
    """Map tox factor py313 -> 3.13, py314 -> 3.14."""
    if not py_tag.startswith("py") or len(py_tag) < 4:
        raise ValueError(f"Invalid python tag: {py_tag!r}")
    digits = py_tag[2:]
    return f"{digits[0]}.{digits[1:]}"


def tox_env_to_python_version(tox_env: str) -> str:
    """Return setup-python version for a tox env (e.g. py314-ha202603 -> 3.14)."""
    return _python_tag_to_version(_tox_python_tag_from_env(tox_env))


def list_github_matrix_entries(
    *, refresh: bool = False, require_phcc: bool = True
) -> list[dict[str, str]]:
    """GHA matrix rows: toxenv + python, derived from the tox env name."""
    return [
        {"toxenv": env, "python": tox_env_to_python_version(env)}
        for env in list_tox_envs(refresh=refresh, require_phcc=require_phcc)
    ]


def load_full_index() -> VersionIndex:
    """Phcc index: versions (phcc -> HA) and ha_python_requires (HA -> Requires-Python)."""
    if INDEX_PATH.is_file():
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return {
            "versions": data.get("versions", {}),
            "ha_python_requires": data.get("ha_python_requires", {}),
        }
    return {"versions": {}, "ha_python_requires": {}}


def list_tox_envs(*, refresh: bool = False, require_phcc: bool = True) -> list[str]:
    """Tox env names from hacs.json min through latest testable HA month."""
    min_month = load_hacs_min_ha_month()
    index = update_version_index_from_pypi(force=refresh)
    versions = index["versions"]
    ha_python_requires = index["ha_python_requires"]
    max_month = resolve_max_ha_month(versions)
    if _month_key(max_month) < _month_key(min_month):
        raise ValueError(
            f"HA test max ({max_month}) is before hacs.json minimum ({min_month})"
        )
    months_with_phcc = {_ha_minor(v) for v in versions.values()}
    envs: list[str] = []
    for month in iter_ha_months(min_month, max_month):
        if require_phcc and month not in months_with_phcc:
            continue
        envs.append(ha_month_to_tox_env(month, versions, ha_python_requires))
    if not envs:
        raise LookupError(
            f"No phcc-backed HA months between {min_month} and {max_month}. "
            "Run: python scripts/phcc_matrix.py --refresh"
        )
    return envs


def _tox_python_tag_from_env(tox_env: str) -> str:
    match = TOX_PYTHON_TAG_RE.match(tox_env)
    if not match:
        raise ValueError(f"Not a HA tox env name: {tox_env!r}")
    return match.group(1)


def parse_ha_month_from_env(env_name: str) -> str | None:
    """Parse HA month from a tox env name (e.g. py313-ha202510 -> 2025.10)."""
    match = HA_FACTOR_RE.search(env_name)
    if not match:
        return None
    digits = match.group(1)
    year = int(digits[:4])
    month = int(digits[4:])
    return f"{year}.{month}"


def _ha_minor(homeassistant_version: str) -> str:
    major, minor, *_ = homeassistant_version.split(".")
    return f"{major}.{minor}"


def _fetch_phcc_version_metadata(version: str) -> dict | None:
    return _fetch_optional_json(
        f"https://pypi.org/pypi/{PHCC_PROJECT}/{version}/json",
        timeout=30,
    )


def _list_phcc_versions_on_pypi() -> list[str]:
    project = _fetch_json(PHCC_PYPI_JSON, timeout=60)
    versions = [v for v in project["releases"] if PHCC_VERSION_RE.match(v)]
    return sorted(versions, key=_version_key)


def _try_list_phcc_versions_on_pypi() -> list[str] | None:
    """Return phcc release versions from PyPI, or None when offline/unreachable."""
    try:
        return _list_phcc_versions_on_pypi()
    except OSError as err:
        logger.warning("PyPI phcc lookup failed: %s", err)
        return None


def load_version_index() -> dict[str, str]:
    """Phcc version -> homeassistant full version (e.g. 2026.3.4)."""
    return load_full_index()["versions"]


def _backfill_ha_python_requires(
    versions: dict[str, str],
    ha_python_requires: dict[str, str],
    *,
    min_month: str | None = None,
    max_month: str | None = None,
) -> None:
    """Fetch Requires-Python from PyPI for homeassistant versions in the test range."""
    ha_versions = set(versions.values())
    if min_month is not None and max_month is not None:
        months_in_range = set(iter_ha_months(min_month, max_month))
        ha_versions = {ha for ha in ha_versions if _ha_minor(ha) in months_in_range}
    for ha_version in sorted(ha_versions, key=_ha_version_key):
        if ha_version in ha_python_requires:
            continue
        requires = _fetch_ha_python_requires(ha_version)
        if requires:
            ha_python_requires[ha_version] = requires


def save_version_index(
    versions: dict[str, str],
    ha_python_requires: dict[str, str] | None = None,
) -> None:
    """Persist phcc index (and optional homeassistant Requires-Python cache)."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ha_python_requires is None:
        ha_python_requires = load_full_index()["ha_python_requires"]
    payload = {
        "versions": dict(
            sorted(versions.items(), key=lambda item: _version_key(item[0]))
        ),
        "ha_python_requires": dict(
            sorted(
                ha_python_requires.items(), key=lambda item: _ha_version_key(item[0])
            )
        ),
    }
    INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _homeassistant_for_phcc(version: str) -> str | None:
    meta = _fetch_phcc_version_metadata(version)
    if meta is None:
        return None
    requires = meta["info"].get("requires_dist") or []
    ha_req = next((r for r in requires if r.startswith("homeassistant==")), None)
    if not ha_req:
        return None
    return ha_req.split("==", 1)[1]


def update_version_index_from_pypi(*, force: bool = False) -> VersionIndex:
    """Fetch metadata only for phcc releases not already in the index."""
    index = load_full_index()
    cached_versions = index["versions"]
    cached_requires = index["ha_python_requires"]
    if force:
        versions: dict[str, str] = {}
        ha_python_requires: dict[str, str] = {}
    else:
        versions = dict(cached_versions)
        ha_python_requires = dict(cached_requires)

    if _index_offline_mode() and not force:
        if not versions:
            raise LookupError(
                f"PHCC_INDEX_OFFLINE set but no index at {INDEX_PATH}. "
                "Build the index in matrix-prep or run online once."
            )
        logger.info(
            "using index only (%d phcc releases, PHCC_INDEX_OFFLINE)",
            len(versions),
        )
    else:
        pypi_versions = _try_list_phcc_versions_on_pypi()
        if pypi_versions is None:
            if force:
                raise LookupError(
                    "Cannot --refresh: PyPI unreachable (existing index left unchanged)"
                )
            if not versions:
                raise LookupError(
                    f"PyPI unreachable and no phcc index at {INDEX_PATH}. "
                    "Run once online to build the index."
                )
            logger.info(
                "using cached index (%d phcc releases, PyPI offline)",
                len(versions),
            )
        else:
            todo = [v for v in pypi_versions if force or v not in versions]
            if todo:
                total = len(todo)
                for i, phcc_version in enumerate(todo, start=1):
                    if i == 1 or i % 25 == 0 or i == total:
                        logger.info(
                            "indexing phcc metadata (%d/%d)...", i, total
                        )
                    ha_version = _homeassistant_for_phcc(phcc_version)
                    if ha_version:
                        versions[phcc_version] = ha_version
        min_month = load_hacs_min_ha_month()
        max_month = resolve_max_ha_month(versions)
        _backfill_ha_python_requires(
            versions, ha_python_requires, min_month=min_month, max_month=max_month
        )
    save_version_index(versions, ha_python_requires)
    return {"versions": versions, "ha_python_requires": ha_python_requires}


def _month_spec_from_index(ha_month: str, versions: dict[str, str]) -> MonthSpec | None:
    entries: list[tuple[tuple[int, ...], str, str]] = []
    for phcc_version, ha_version in versions.items():
        if _ha_minor(ha_version) != ha_month:
            continue
        entries.append((_version_key(phcc_version), phcc_version, ha_version))
    if not entries:
        return None

    entries.sort(key=lambda item: item[0])
    all_phcc = sorted(_version_key(v) for v in versions)
    lo_ver = entries[0][1]
    hi_pv = entries[-1][0]
    hi_ha = entries[-1][2]
    idx = all_phcc.index(hi_pv)
    if idx + 1 < len(all_phcc):
        upper = ".".join(str(p) for p in all_phcc[idx + 1])
        spec = f"{PHCC_PROJECT}>={lo_ver},<{upper}"
    else:
        spec = f"{PHCC_PROJECT}>={lo_ver}"
    year = int(ha_month.split(".")[0])
    return MonthSpec(
        ha_month=ha_month,
        phcc_spec=spec,
        pycares_pin=year == 2025,
        homeassistant=hi_ha,
    )


def get_month_spec(ha_month: str, *, refresh: bool = False) -> MonthSpec:
    """Resolve install spec for an HA month; updates PyPI index on demand."""
    versions = update_version_index_from_pypi(force=refresh)["versions"]
    spec = _month_spec_from_index(ha_month, versions)
    if spec is not None:
        return spec

    raise LookupError(
        f"No {PHCC_PROJECT} release found for Home Assistant {ha_month}. "
        "Check the tox factor (e.g. ha202603) or run: python scripts/phcc_matrix.py --refresh"
    )


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch all phcc version metadata from PyPI",
    )
    parser.add_argument(
        "--github-matrix",
        action="store_true",
        help="Print GHA matrix JSON [{toxenv, python}, ...] (min from hacs.json)",
    )
    parser.add_argument(
        "ha_month",
        nargs="?",
        help="HA month like 2026.3 (optional; prints derived matrix if omitted)",
    )
    args = parser.parse_args()

    if args.github_matrix:
        _out(json.dumps(list_github_matrix_entries(refresh=args.refresh)))
        return

    if not args.ha_month:
        envs = list_tox_envs(refresh=args.refresh)
        versions = load_version_index()
        _out(f"Index: {INDEX_PATH} ({len(versions)} phcc releases)")
        _out(
            f"Test range: {load_hacs_min_ha_month()} .. "
            f"{resolve_max_ha_month(versions)} ({len(envs)} tox envs)"
        )
        for env in envs:
            month = parse_ha_month_from_env(env)
            if month is None:
                continue
            spec = _month_spec_from_index(month, versions)
            if spec:
                _out(f"  {env}: {spec.phcc_spec} (HA {spec.homeassistant})")
        return

    spec = get_month_spec(args.ha_month, refresh=args.refresh)
    versions = load_version_index()
    _out(f"Index: {INDEX_PATH} ({len(versions)} phcc releases)")
    _out(spec.phcc_spec)
    if spec.pycares_pin:
        _out("pycares>=4.0.0,<5")


if __name__ == "__main__":
    main()
