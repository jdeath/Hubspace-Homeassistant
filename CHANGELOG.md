# Changelog

All notable changes to the Hubspace Home Assistant integration are documented here.
Release notes on GitHub Releases are kept in sync for recent versions so HACS update
notifications stay useful.

## 8.2.1

- Fix: Hide brightness while **Night Light Mode** is active (`supported_color_modes`
  narrows to on/off) so HA no longer shows a no-op slider
  ([#253](https://github.com/jdeath/Hubspace-Homeassistant/issues/253))

## 8.2.0

- Break: Night Light is no longer a separate `light.*` entity. Fixtures that
  expose API `color-mode: night-light` use the **Night Light Mode** effect on
  the main light instead ([#232](https://github.com/jdeath/Hubspace-Homeassistant/issues/232),
  [#253](https://github.com/jdeath/Hubspace-Homeassistant/issues/253)).
- Fix: `light.turn_off` targeting all lights no longer turns Hubspace track /
  vanity fixtures back on via a hidden night-light entity ([#253](https://github.com/jdeath/Hubspace-Homeassistant/issues/253)).

## 8.1.1

- Pin aioafero to git branch `fix/device-splits` (pre-release): split clones
  carry `SplitDeviceId` so toggles whose instance names contain the split
  token (e.g. `light-sensor-enabled`) poll and write the parent metadevice
  instead of a synthetic `{id}-light` path
  ([#254](https://github.com/jdeath/Hubspace-Homeassistant/issues/254))
- Fix split entity display names to use `resource.instance` instead of
  parsing the synthetic id with `rsplit`

## 8.1.0

- Add dehumidifier support (Vissani `VAD50PS1AWTS`, Hubspace device class
  `dehumidifier`) as a `humidifier` entity: power, mode, current and target
  humidity, plus `Fan Speed` and `Pump` selects
  ([#259](https://github.com/jdeath/Hubspace-Homeassistant/issues/259)).
- Add `Check Filter`, `EEPROM Error`, and `Evaporator Temperature Sensor Failed`
  diagnostic binary sensors reported by the dehumidifier.
- Require `aioafero==9.2.0`.

## 8.0.0

- Break: Require `aioafero==9.0.1`. Login/reauth use `AferoAuth`; the bridge
  takes username + refresh token + Home Assistant's shared HTTP session (no
  password at runtime). Downgrade without removing/re-adding the integration is
  not supported.
- Break: Account password is no longer stored in the config entry; only the
  refresh token is persisted (`token` data key renamed to `refresh_token`).
  Reauth prompts for the password when needed.
- Break: Minimum Home Assistant version is **2026.7** (`aiohttp>=3.14.3`
  required by aioafero 9.0).
- Fix: Removed or inaccessible devices no longer spam Forbidden state polls
  every interval — aioafero marks them unavailable and pauses retries until the
  next successful discovery.

## 7.0.0

- Break: Primary entity IDs change — naming follows HA `has_entity_name` (device name
  only, no class-name suffix). Example: `light.laundry_room_light` → `light.laundry_room`.
  Update automations/dashboards. Instance and split entities are unchanged.
- Require `aioafero==8.0.0`: dual-channel RGB+WW fixtures stay one API light;
  each color/white channel is a separate HA light entity. Per-channel brightness
  lives on `Light.channels` (not Number sliders)
  ([#160](https://github.com/jdeath/Hubspace-Homeassistant/issues/160),
  [#218](https://github.com/jdeath/Hubspace-Homeassistant/issues/218),
  [#230](https://github.com/jdeath/Hubspace-Homeassistant/issues/230))
- aioafero prefers API `color-mode: mixed` when both channels are on, and moves
  back to exclusive `color` / `white` when a channel is turned off
- Fix state updates that omitted or guessed `functionClass` / `functionInstance`
  (e.g. fans sending `functionInstance: null` instead of `fan-power`), which could
  make devices ignore commands ([#240](https://github.com/jdeath/Hubspace-Homeassistant/issues/240))

## 6.0.3

- Fix portable AC power switch having no effect ([#234](https://github.com/jdeath/Hubspace-Homeassistant/issues/234))
- Require aioafero `7.0.9`

## 6.0.2

- Add Night Light mode support for fixtures that expose it (e.g. Hampton Bay Penrose) ([#232](https://github.com/jdeath/Hubspace-Homeassistant/issues/232))
- Require aioafero `7.0.8`

## 6.0.1

- Fix split lights not being controllable
- Fix white mode for lights

## 6.0.0

- Break: Some lights that were split (such as ones with trim) now have new entity IDs. Any automations need to be updated to reflect the new IDs
- Implement better support for split lights ([#211](https://github.com/jdeath/Hubspace-Homeassistant/issues/211))

## 5.10.0

- Enable full support for fahrenheit for climate devices. The unit to use is determined by the
  selected units within Settings -> System -> General -> Unit system. ([#198](https://github.com/jdeath/Hubspace-Homeassistant/issues/198))
- Add Swing on/off to climate devices that support this functionality ([#187](https://github.com/jdeath/Hubspace-Homeassistant/issues/187))
- Fix an issue where performing a reload would lose all device names ([#199](https://github.com/jdeath/Hubspace-Homeassistant/issues/199))

## 5.9.2

- Fix an issue where the integration stated it was ready too early ([#189](https://github.com/jdeath/Hubspace-Homeassistant/issues/189))

## 5.9.1

- Fix an issue during initialization to generated a blocking call

## 5.9.0

- Support OTP login workflow ([#188](https://github.com/jdeath/Hubspace-Homeassistant/issues/188))
- Fix an issue where reauth or reconfig did not have a translation
- Ensure that only one entry can be present at a time

## 5.8.0

- Add alarm panels ([#180](https://github.com/jdeath/Hubspace-Homeassistant/issues/168))

## 5.7.1

- Fix an issue where auth would not retry ([#169](https://github.com/jdeath/Hubspace-Homeassistant/issues/169))

## 5.7.0

- Display version information for devices

## 5.6.0

- Enable support for all aioafero clients ([#168](https://github.com/jdeath/Hubspace-Homeassistant/issues/180))

## 5.5.0

- Enable switch control for lights that utilize toggles ([#172](https://github.com/jdeath/Hubspace-Homeassistant/issues/172))
- Fix an issue where sensors would not appear for docker containers ([#176](https://github.com/jdeath/Hubspace-Homeassistant/issues/176))

## 5.4.0

- Add support for the light LCN3002LM-01 WH ([#160](https://github.com/jdeath/Hubspace-Homeassistant/issues/160))

## 5.3.1

- Fixed an issue where a failure during auth produced an Unhandled exception ([#169](https://github.com/jdeath/Hubspace-Homeassistant/issues/169))

## 5.3.0

- Add support for Portable ACs ([#162](https://github.com/jdeath/Hubspace-Homeassistant/issues/162))
- Update climate devices to adjust more closely to Hubspace
- Fix an issue where Thermostats could incorrectly use Auto

## 5.2.3

- Update linter to ruff

## 5.2.2

- Fix battery percentage not showing ([#164](https://github.com/jdeath/Hubspace-Homeassistant/issues/164))

## 5.2.1

- Fix Action calls from the UI

## 5.2.0

- Fully implement exhaust fans ([#152](https://github.com/jdeath/Hubspace-Homeassistant/issues/152))

## 5.1.0

- Permanently hide secrets within HA logs

## 5.0.0

- BREAK: Binary Sensor names are more accurate but have new entity IDs
- Implement climate / thermostats ([#143](https://github.com/jdeath/Hubspace-Homeassistant/issues/143))

## 4.6.0

- Binary Sensor / Sensor is now identified on a per-resource basis, rather than root-device

## 4.5.0

- Convert to aioafero==2.0.0
- Update minimum version of HA to 2024.8 ([#149](https://github.com/jdeath/Hubspace-Homeassistant/issues/149))

## 4.4.2

- Fixed an issue where the integration would create a new login to Hubspace each time it started

## 4.4.1

- Fixed an issue where valves were labeled as fans
- Fixed an issue where valves would not show the correct state

## 4.4.0

- Implement reauth workflow
- Gracefully handle issues with Hubspace API

## 4.3.0

- Convert to aiohubspace==1.x
- Added a device for the Hubspace account
- Added a button to the Hubspace account device for generating debug logs
- Added a button to the Hubspace account device for generating raw
- Fixed an issue where Binary Sensors would not display the proper value
- Fixed an issue in config flow reauth
- Fixed an issue for fans while effect could be improperly displayed
- Fixed an issue where adding new lights to the Hubspace account would cause a UHE
- Fixed an issue where sensors could cause a UHE for the value ([#132](https://github.com/jdeath/Hubspace-Homeassistant/issues/132))
- Fixed an issue where adding new valves to the Hubspace account would cause a UHE
- Fixed an issue where valves would always show as open

## 4.2.0

- Added supported for Glass Door control ([#127](https://github.com/jdeath/Hubspace-Homeassistant/issues/127))

## 4.1.1

- Fix an issue where locks were not controllable ([#128](https://github.com/jdeath/Hubspace-Homeassistant/issues/128))

## 4.1.0

- Re-implement the action / service send_command ([#94](https://github.com/jdeath/Hubspace-Homeassistant/issues/94))

## 4.0.1

- Fixed an issue where fans could cause an UHE if they did not support
  some functionality ([#125](https://github.com/jdeath/Hubspace-Homeassistant/issues/125))

## 4.0.0

- BREAK: Sensors have new names. Old sensors marked as unavailable can be removed.
- Enabled customization of Hubspace polling intervals
- Created a button for generating debug data dumps
- Backend now uses aiohubspace to talk to Hubspace
- Removed logic on setting states within Home Assistant
- Devices are only created from the "top-level" device, rather than individually
- Added models for HPDA110NWBP and HPSA11CWB

## 3.3.0

- Add binary sensors for freezers

## 3.2.0

- Enable a custom timeout during initial configuration
