# Overview

This repository provides an integration between Hubspace and Home Assistant. Due to the cloud-first
nature of Hubspace devices, an internet connection needs to be available, along with the Hubspace servers.

## Supported devices

Afero device classes are mapped into Home Assistant entities from what the
cloud reports. Support is **capability-based**: a feature appears only when that device
exposes it. Not every fixture maps cleanly; dumps from Troubleshooting help fill gaps.

### Common Hubspace types we map

These `deviceClass` values (and close variants) are expected to discover into HA:

- Ceiling / exhaust fans
- Freezers / related error binary sensors when present
- Lights (including dual-channel color + white fixtures)
- Locks
- Outlets and switches (including glass door / transformer-style switches)
- Portable ACs and thermostats
- Security systems (panel + related sensors)
- Water timers (valves)

Combo parents such as `ceiling-fan` may be skipped as a root device while child fan/light
resources are still created.

### Home Assistant platforms

- Alarm control panel [`alarm_control_panel`] — Security system arm home/away,
  disarm, trigger when supported
- Binary sensor [`binary_sensor`] — Problems, motion, humidity threshold,
  tamper, and similar flags
- Button [`button`] — Account-level debug / dump actions on the Hubspace device
- Climate [`climate`] — Thermostats and portable ACs — HVAC modes, fan mode,
  current/target temperature (and range when supported)
- Fan [`fan`] — On/off, speed, direction, preset (e.g. breeze) when exposed
- Light [`light`] — On/off, brightness, color temp, RGB, effects; dual-channel
  fixtures present as separate color/white lights; night-light when exposed
- Lock [`lock`] — Lock / unlock
- Number / Select [`number` / `select`] — Numeric settings and mode pickers
  (common on exhaust fans and similar)
- Sensor [`sensor`] — Diagnostics such as battery, watts, voltage, Wi‑Fi RSSI,
  security history
- Switch [`switch`] — On/off for outlets, switches, and split power toggles
- Valve [`valve`] — Open / close (water timers)

If a device is missing or incomplete, see [Troubleshooting](#troubleshooting).

## Changelog

Full history is in [CHANGELOG.md](CHANGELOG.md). HACS update notifications use
[GitHub Releases](https://github.com/jdeath/Hubspace-Homeassistant/releases).

## Installation

Add this repo as a custom repository in [HACS](https://hacs.xyz/). Add the hubspace integration.

Clicking this badge should add the repo for you:
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jdeath&repository=Hubspace-Homeassistant&category=integration)

## Configuration

After Hubspace has been added through HACs, the
configuration continues within the UI like other integrations. First select `Settings`
on the navigation bar, then select `Devices & services`, ensure you are on the
`Integrations` tab, then finally select `ADD INTEGRATION` at the bottom right
of the page. Search for `Hubspace` and enter your username and password and
click `SUBMIT`. Entities should start appearing shortly after clicking submit.

After discovered, the poll time can be configured for quicker or longer
polling intervals. By default, Hubspace is polled once every 30 seconds.

### Configuration Troubleshooting

- Unable to authenticate with the provided credentials

  - Ensure the provided credentials can authenticate to Hubspace

- Connection timed out when reaching the server

  - Increase the timeout

# Troubleshooting

Device troubleshooting may require a data dump from Hubspace. This can
be generated within the UI, but will need to be retrieved with something
that can access Home Assistants Filestore.

- Navigate to the Hubspace Devices

  - Settings -> Devices & services -> Integrations -> Hubspace

- Click on devices on the navigation bar underneath the Hubspace logo
- Click on the device named labeled `hubspace-<email_address>`
- Click `Press` on `Generate Debug` underneath Controls
- Open File Editor
- Click the folder icon on the top left
- Navigate to custom_components -> hubspace
- Download the required files:

  - `_dump_hs_devices.json`: Anonymized device dumps consumed by the Hubspace integration

# FAQ

- I have a device in Hubspace that is not added to Home Assistant

  - Check the logs for any warning / errors around hubspace and report the issue.
  - If no warning / error messages exist around Hubspace, the device type is likely
    not supported. Refer to the troubleshooting section to grab anonymized logs and
    open a new issue with the logs and state the device that did not discover

- I have a device and its missing functionality

  - Refer to the troubleshooting section to grab anonymized logs and
    open a new issue with the logs and state the device that is not working
    along with the broken functionality

- I have a device and its functionality is not working

  - Refer to the troubleshooting section to grab anonymized logs and
    open a new issue with the logs and state the device that is not working
    along with the broken functionality
  - If the developers are unable to solve the problem with the anonymized data,
    the raw data may need to be provided

- I have a device that does not display the correct model

  - Generate the debug logs and create an issue on GitHub.

- I enabled MFA within my app but I was not forced to re-login.

  - Tokens are not invalidated when you enable MFA and must invalidate them manually. For Hubspace,
    this is done by going to "Manage Account" and clicking "Where You're Signed In", then clicking
    "SIGN OUT OF ALL OTHER DEVICES". Once signed out, the existing token could be valid for up to
    two more minutes. Once the current token is expired, Home Assistant will show there is a repair
    available for "Authentication expired for <email>".

- I adjusted Home Assistants Unit system and now the values are displaying incorrectly

  - After updating the Unit system, you must also reload the integration for the values to show correctly. This
    can be accomplished by going to Settings -> Devices & services -> Hubspace -> Triple dots -> Reload.

- I upgraded Hubspace and my RGB / flushmount light shows extra entities or wrong brightness

  - Version 7.0.0 keeps dual-channel lights as **one** API light (not separate
    aioafero `_color` / `_white` light resources). In Home Assistant they present as
    two light entities (color + white) on one device — including RGBCW strips and
    flushmounts. Channel brightness is not exposed as Number entities — use each
    light's slider. Reload after upgrading so Home Assistant drops stale entities.
  - Turn a channel off with that light's Off control; aioafero adjusts `color-mode`
    (including leaving `mixed` when only one channel remains).
  - If automations reference old entity IDs from earlier split-light changes, update them in
    Settings → Devices & services → Entities.

_Thanks to everyone who starred my repo! To star it click on the image below, then it will be on top right. Thanks!_

[![Star History Chart](https://api.star-history.com/svg?repos=jdeath/Hubspace-Homeassistant&type=Date)](https://star-history.com/#jdeath/Hubspace-Homeassistant&Date)
