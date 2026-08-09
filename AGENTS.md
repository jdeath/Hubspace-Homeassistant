# AI agent guide — Hubspace Home Assistant

Custom integration that maps Afero / Hubspace cloud devices into Home Assistant.

**Device and protocol logic belongs in [aioafero](https://github.com/Expl0dingBanana/aioafero)**
(see that repo’s `AGENTS.md`). This integration owns HA config flow, config
entry lifecycle, entity platforms, and wiring to `AferoBridgeV1`. Versions and
pins live in `manifest.json` / `hacs.json` — read those instead of hard-coding
them here.

## Commands and quality gate

Prefer **uv** + **tox** (see [docs/testing.md](docs/testing.md)). Do not treat
`README.md` as the testing guide — HACS renders the README only.

```bash
uv sync                                          # or: pip install -r test-requirements.txt
uv run tox -av                                   # list lint + HA month envs (pyXXX-haYYYYMM)
uv run tox -e lint                               # pre-commit (ruff, format, yaml, …)
uv run tox -e <pyXXX-haYYYYMM>                   # one HA month from -av
uv run tox run-parallel -p auto -o --skip-env lint   # full matrix (optional before PR)
uv run tox -e <pyXXX-haYYYYMM> -- tests/test_light.py -q
```

HA env list comes from `hacs.json` + `scripts/phcc_matrix.py` via `toxfile.py`
(same range as CI). First HA env run needs network to build the phcc index.
Lint rules live in `pyproject.toml` and `.pre-commit-config.yaml` — fix what
`tox -e lint` reports. CI also runs hassfest and HACS validation workflows.

Pytest always runs with `--cov=custom_components.hubspace --cov-report term-missing`
(`pytest.ini`). Read the missing-lines report after every test run and cover new
or changed code in `custom_components/hubspace/`. There is **no**
`--cov-fail-under` / Codecov 100% gate (unlike aioafero). Parallel tox uses a
per-env `COVERAGE_FILE` so jobs do not clobber each other.

Before a PR: **lint** + at least one relevant HA tox env with coverage reviewed
for your changes. Full parallel matrix when touching shared bridge / auth / CI
tooling.

## Auth and config entry

- **Single entry:** `manifest.json` sets `single_config_entry`. One Hubspace
  account per HA instance; unique_id is the username.
- **Runtime:** `HubspaceBridge` builds
  `AferoBridgeV1(username, refresh_token, hass_session, …)`. No password on the
  bridge.
- **Stored token key:** config entry uses `CONF_REFRESH_TOKEN` (`"refresh_token"`).
  The value is aioafero’s refresh token (`token_data.refresh_token`). The v6
  migration renames the legacy `"token"` key when upgrading older entries.
- **Login / reauth / OTP:** `AferoAuth.for_login` + `submit_otp` in
  `config_flow.py`. Password is handshake-only and must not remain on the entry.
- **Entry data vs options:** data holds username, client, and refresh token.
  Timeout and polling interval live in **options** (keys and limits in
  `const.py` / options flow).
- **Config entry schema:** `VERSION_MAJOR` / `VERSION_MINOR` in `const.py`.
  Migrations live in `__init__.py`.
  Bump those only when the entry schema changes, and add migration tests.
- **Session:** use `aiohttp_client.async_get_clientsession(hass)` — do not open a
  private `ClientSession` for the bridge.

## Architecture

```
config_flow / migrations → HubspaceBridge → AferoBridgeV1 (aioafero)
                         → platform entities (light, fan, climate, …)
```

- `bridge.py` — account connection, initialize / close, reauth trigger.
- `device.py` — HA device registry for discovered Afero devices.
- `entity.py` + platform modules — map aioafero models to HA entities.
  Base entities use `has_entity_name`; changing primary entity ID patterns is a
  user-visible break (document in `CHANGELOG.md`).
- Controllers and cloud I/O stay in aioafero; call controller / `set_state`
  helpers rather than inventing API payloads here.
- Entities do not poll (`should_poll` is false); cloud polling is bridge /
  aioafero (`iot_class` in `manifest.json`).

### Lights (gotchas)

- **Dual-channel:** one aioafero light can become separate HA color + white
  entities; channel brightness lives on those lights (not Number sliders). See
  `light.py` and the README FAQ.
- **Night light:** separate entity; bridge keeps previous mode / on state when
  night light is toggled — do not treat it as a normal color-mode on the main
  light.

## Layout

| Path                          | Role                                                     |
| ----------------------------- | -------------------------------------------------------- |
| `custom_components/hubspace/` | Integration code + `manifest.json` (runtime pins)        |
| `tests/`                      | pytest + helpers (`tests/utils.py`, `conftest` fixtures) |
| `tests/device_dumps/`         | Anonymized device JSON for fixtures                      |
| `scripts/tox_ha_install.py`   | Per-env HA/phcc install for tox                          |
| `scripts/phcc_matrix.py`      | HA month ↔ Python / phcc matrix                         |
| `hacs.json`                   | Minimum HA version (floor for tox + HACS)                |
| `CHANGELOG.md`                | Release history (not the HACS landing page)              |
| `README.md`                   | HACS-facing overview                                     |

Also expect `services.py` / `services.yaml`, and keep `strings.json` in sync with
`translations/en.json` for flow/options/errors.

### Version bump checklist

| Change                             | Update                                                         |
| ---------------------------------- | -------------------------------------------------------------- |
| Integration release / aioafero pin | `manifest.json` `"version"` + `"requirements"`, `CHANGELOG.md` |
| Minimum Home Assistant             | `hacs.json` (tox/CI floor follows)                             |
| Config entry schema                | `VERSION_*` in `const.py`, migration in `__init__.py`, tests   |

Local `uv sync` may use an editable aioafero path from `pyproject.toml`; tox
installs the **manifest** pin. Do not assume they are the same.

## Adding or changing a platform

Follow an existing platform (e.g. `fan.py`, `switch.py`): entity subclass,
discover from bridge/device setup, register in `PLATFORMS` / setup hooks as
peers do. Prefer capability checks from aioafero models over hard-coding device
SKUs. Tests use `mocked_bridge` / `mocked_entry` and helpers in `tests/utils.py`
(device dumps under `tests/device_dumps/`). Document user-visible breaks in
`CHANGELOG.md`.

If the cloud behavior is wrong or missing, fix or extend **aioafero** first,
then consume it here.

## Secrets and dumps

Never commit credentials, live tokens, or dumps with PII. Prefer anonymized
device dumps (see README troubleshooting). Password must not appear in entry
data or logs.

## Docs and releases

- HACS shows `README.md` and GitHub **Release** notes on update — keep README
  lean; put history in `CHANGELOG.md`.
- `docs/testing.md` is for contributors/agents, not HACS.
- This repo has no `.github/copilot-instructions.md`; before push, still review
  the diff for secrets, auth/session rules, and migration/options mistakes.

## Further reading

[CHANGELOG.md](CHANGELOG.md) · [README.md](README.md) · [docs/testing.md](docs/testing.md) ·
[CONTRIBUTING.md](CONTRIBUTING.md) · [aioafero AGENTS.md](https://github.com/Expl0dingBanana/aioafero/blob/main/AGENTS.md)
