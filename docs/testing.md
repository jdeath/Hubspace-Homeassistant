# Testing and CI

This document describes how integration tests are run locally and in GitHub Actions. It is **not** shown in HACS (the HACS UI uses `README.md` only).

## Quick start (local)

Do these steps in order the first time you run tests on a machine.

1. **Clone the repo** and open a shell in the repository root.

2. **Install Python interpreters** used by the matrix (today **3.13** and **3.14**). Each HA month’s tox env uses the version Home Assistant declares on PyPI (`Requires-Python`); see [New Python for newer HA months](#new-python-for-newer-ha-months) when another version appears. List months and Python tags with `python scripts/phcc_matrix.py` or `tox -av`.

3. **Install dev headers on Linux** for every interpreter you will use, e.g. `python3.13-dev` and `python3.14-dev` (or your distro’s equivalent). Without them, HA dependency installs can fail with `Python.h: No such file or directory`.

4. **Create a venv and install test tools** (includes tox ≥ 4.29):

   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -r test-requirements.txt
   ```

5. **Lint:**

   ```bash
   tox -e lint
   ```

6. **One HA release month** (name from `tox -av` or `python scripts/phcc_matrix.py`):

   ```bash
   tox -e py313-ha202510
   ```

   First run may take several minutes while `scripts/phcc_matrix.py` builds `.tox/phcc_version_index.json` from PyPI (network required). Later runs reuse the cache.

7. **Full matrix (optional)** — after lint passes:

   ```bash
   tox run-parallel -p auto -o --skip-env lint
   ```

   Tox 4 uses `run-parallel`, not `-j`. `-o` streams output live.

**Subset of tests:** append paths after `--`, e.g. `tox -e py313-ha202510 -- tests/test_light.py -q`.

**Inspect CI matrix without running tests:** `python scripts/phcc_matrix.py --github-matrix`.

## Overview

Tests use [tox](https://tox.wiki/) with one environment per supported **Home Assistant release month**. Each environment installs:

- **Home Assistant** and **pytest-homeassistant-custom-component** (phcc) for that month
- **Integration dependencies** from `custom_components/hubspace/manifest.json` (same pins HACS uses)
- **Test tools** from `test-requirements.txt`

Linting runs separately via pre-commit (`tox -e lint`).

### Local vs CI matrix (aligned)

Both use **`hacs.json`** (minimum month) and **`scripts/phcc_matrix.py`** (through latest PyPI month, phcc-backed, Python from `Requires-Python`):

|           | Mechanism                                                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **CI**    | `matrix-prep` → `--github-matrix` → one job per `toxenv`                                                                                    |
| **Local** | Root **`toxfile.py`** → extends `envlist` with the same names; `tox.ini` `basepython` factors (`py313`, `py314`, …) match env name prefixes |

Committed **`tox.ini`** only defines shared `[testenv]` settings and `lint`; `toxfile.py` supplies HA env names from `hacs.json`.

## Sources of truth

| What                           | File / tool                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Minimum HA version to test     | `hacs.json` → `"homeassistant"` (e.g. `2025.7`)                                                                                |
| Maximum HA month to test       | Latest release on PyPI (`homeassistant` package), via `scripts/phcc_matrix.py`                                                 |
| Integration runtime deps       | `custom_components/hubspace/manifest.json` → `"requirements"`                                                                  |
| phcc / exact HA pin per month  | `scripts/phcc_matrix.py` + `.tox/phcc_version_index.json`                                                                      |
| Python version per tox env     | PyPI `Requires-Python` on each `homeassistant` release (via phcc index)                                                        |
| Local tox env names            | `toxfile.py` + `phcc_matrix.list_tox_envs()`                                                                                   |
| Tox reinstall on manifest bump | `toxfile.py` copies `manifest.json` `"requirements"` into each HA env’s `deps` and `setenv` (same list as `tox_ha_install.py`) |

There is **no** `requirements.txt` for the integration; tox installs from the manifest.

## Prerequisites (reference)

- **Python** — versions on `PATH` for every env `tox -av` lists.
- **tox ≥ 4.29** — from `test-requirements.txt` (loads `toxfile.py`).
- **Dev headers** — per interpreter on Linux (see quick start step 3).
- **Network** — first phcc index build or `--refresh` contacts PyPI.

Parallel runs use per-env `COVERAGE_FILE` in `tox.ini` so `.coverage` files do not clash.

### Why startup still feels slow

Not everything is cached across a tox run. What is reused vs what runs every time:

| Layer                          | Cached?      | Notes                                                                                                                 |
| ------------------------------ | ------------ | --------------------------------------------------------------------------------------------------------------------- |
| `.tox/py313-ha…` venv          | Yes, per env | Recreated when `deps` / `setenv` hash changes (manifest, test-requirements).                                          |
| pip wheels                     | Yes          | `~/.cache/pip` (or tox/pip cache). First install of homeassistant + phcc per env is still large.                      |
| `.tox/phcc_version_index.json` | On disk      | Avoids re-indexing hundreds of phcc releases, but **without offline mode** each install used to re-query PyPI (~30s). |
| pytest-homeassistant boot      | No           | Each env/run loads Home Assistant for tests (inherent cost).                                                          |
| Full matrix                    | 11 envs      | `run-parallel` builds **one venv per HA month**; first-time cost × N.                                                 |

After the phcc index exists, `toxfile.py` sets `PHCC_INDEX_OFFLINE=1` (in each env’s `setenv` and in the **tox parent process** before `list_tox_envs()` for `run-parallel`). Without that parent step, every `run-parallel` still hit PyPI for ~30s before any env started. Refresh the index when needed: `PHCC_INDEX_OFFLINE=0 python scripts/phcc_matrix.py --refresh`.

For day-to-day dev, prefer `tox -e py313-ha202510` (one month) over `run-parallel` unless you need the full matrix.

## Helper scripts

### `scripts/phcc_matrix.py`

Builds and maintains the mapping from HA month → phcc version range → tox env name.

| Command                                         | Purpose                                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| `python scripts/phcc_matrix.py`                 | List tox envs and phcc spec for hacs.json .. latest PyPI (uses / updates index) |
| `python scripts/phcc_matrix.py --refresh`       | Re-fetch all phcc metadata from PyPI                                            |
| `python scripts/phcc_matrix.py --github-matrix` | JSON matrix for CI                                                              |

**Index cache:** `.tox/phcc_version_index.json` (gitignored). Stores phcc → HA mappings and cached `Requires-Python` per HA release. First run or `--refresh` contacts PyPI; later runs are incremental.

**`PHCC_INDEX_OFFLINE=1`:** use the on-disk index only (no PyPI list or metadata fetch). CI matrix jobs set this after downloading the index from **matrix-prep**.

### `scripts/tox_ha_install.py`

Tox `install_command` hook. For HA envs it installs `test-requirements.txt`, manifest requirements, phcc (which pins `homeassistant`), and `pycares>=4.0.0,<5` for 2025.x months when needed (aiodns compatibility).

### `toxfile.py`

Tox 4 plugin loaded from the repo root. Appends HA env names to `envlist` so `tox run-parallel` matches CI without a long static list in git. Python interpreters come from `basepython` factors in `tox.ini` (add a line when a new `py315` prefix appears).

- `tox -e lint` — does not load the phcc index for env registration.
- `tox -e py313-ha202510` or `tox -e lint,py313-ha202510` — registers only the named HA env(s); does not enumerate the full matrix.
- `tox -av` / `tox run-parallel` — discovers all HA envs via `list_tox_envs()` (may update the index).

## GitHub Actions

Workflow: `.github/workflows/ci.yaml`

1. **lint** — `tox -e lint`
2. **matrix-prep** — builds/updates `.tox/phcc_version_index.json` once, runs `--github-matrix`, uploads the index as a workflow artifact
3. **homeassistant** — one job per matrix row; downloads the index artifact, sets `PHCC_INDEX_OFFLINE=1`, then `tox -e ${{ matrix.toxenv }}` (no per-job PyPI phcc indexing)

CI installs `pip install -r test-requirements.txt` before tox in **lint** and **homeassistant** (ensures `tox>=4.29` matches `tox.ini`; HA envs still install test deps into the tox venv via `tox.ini`).

Caches: pip wheels (per job, via `setup-python`); phcc index warm-start in **matrix-prep** only (`actions/cache` on `.tox/phcc_version_index.json`). Matrix jobs use the artifact from the same workflow run, not a separate index rebuild. Full tox venvs are **not** cached in CI.

## Maintenance

### Raise minimum supported HA (HACS)

1. Update `hacs.json` → `"homeassistant"`.
2. Commit `hacs.json`. CI and local tox pick up the new floor on the next run (no `tox.ini` edit).

### New HA month released

Usually **no manual edit**: max month comes from PyPI. After phcc publishes a release for that month, the next CI run and the next local `tox` invocation include it.

### New Python for newer HA months

When Home Assistant ships requiring a newer Python (e.g. 3.15), PyPI’s `Requires-Python` on that `homeassistant` wheel is read automatically. No cutoff constant to maintain.

1. Add `py315: python3.15` under `[testenv]` `basepython` in `tox.ini` (tox matches the `py315` prefix in env names).
2. Install that Python locally (and `python3.15-dev` on Linux if wheels build from source).
3. CI `setup-python` uses the version from `--github-matrix` (`py315` → `3.15`).

New env names (e.g. `py315-ha202607`) appear automatically once step 1 is in place.

## Troubleshooting

| Symptom                                                         | Likely cause                                                                                                                                                                                    |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pytest` not found / install skipped                            | Ensure `tox.ini` has `deps = -rtest-requirements.txt` and `package = skip`                                                                                                                      |
| `Python.h: No such file or directory` during install            | Install dev package for that env’s Python (`python3.13-dev`, `python3.14-dev`, …)                                                                                                               |
| `Lingering task` after `test_reload`                            | Bridge must call `api.close()` on unload (`HubspaceBridge.async_reset`)                                                                                                                         |
| One env fails in parallel with exit code 3, passes alone        | Stale shared `.coverage`; fixed via per-env `COVERAGE_FILE` in `tox.ini`                                                                                                                        |
| Very slow first tox run                                         | Building phcc index from PyPI; reuse `.tox/phcc_version_index.json`                                                                                                                             |
| pip appears to hang                                             | Avoid unpinned phcc + separate `homeassistant==`; use `tox_ha_install` only                                                                                                                     |
| HA envs missing from `tox -av`                                  | tox older than 4.29 or `toxfile.py` not loaded; upgrade tox and run from repo root                                                                                                              |
| `tox -e lint` slow on first run                                 | `tox -av` / `run-parallel` builds the phcc index; `tox -e lint` or `tox -e py313-ha…` alone avoids full matrix discovery                                                                        |
| PyPI unreachable / offline                                      | Reuse `.tox/phcc_version_index.json` if present; build index once online. `--refresh` needs network                                                                                             |
| Wrong `aioafero` in tox (missing `gather_discovery_data`, etc.) | Stale env from before `toxfile.py` wired manifest into `deps`; run tox once (install reruns) or `tox … --recreate` if needed. Changing `manifest.json` should invalidate install automatically. |
