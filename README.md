# Overview

This repository provides an integration between Hubspace and Home Assistant. Due to the cloud-first
nature of Hubspace devices, an internet connection needs to be available, along with the Hubspace servers.

## Supported Devices

A supported device indicates that is maps into Home Assistant. Please note that not all
devices will correctly map and may require further troubleshooting. The supported Devices
are as follows:

- Fan

  - On/Off
  - Speed
  - Preset mode

- Freezer

  - Error sensors

- Lock

  - Lock / Unlock

- Light

  - On/Off
  - Color Temperature
  - Color Sequences
  - Dimming
  - RGB

- Outlet

  - On/Off

- Portable AC

  - HVAC Mode
  - Fan Mode
  - Temperature
  - Target Temperature

- Smart Glass

  - On/Off

- Switch

  - On/Off

- Thermostat

  - HVAC Mode
  - Fan Mode
  - Temperature
  - Target Temperature

- Transformer

  - On/Off

- Water Valve

  - Open / Close

## Changelog

- 5.7.0

  - Display version information for devices

- 5.6.0

  - Enable support for all aioafero clients ([#180](https://github.com/jdeath/Hubspace-Homeassistant/issues/180))

- 5.5.0

  - Enable switch control for lights that utilize toggles ([#172](https://github.com/jdeath/Hubspace-Homeassistant/issues/172))
  - Fix an issue where sensors would not appear for docker containers ([#176](https://github.com/jdeath/Hubspace-Homeassistant/issues/176))

- 5.4.0

  - Add support for the light LCN3002LM-01 WH ([#160](https://github.com/jdeath/Hubspace-Homeassistant/issues/160))

- 5.3.1

  - Fixed an issue where a failure during auth produced an Unhandled exception ([#169](https://github.com/jdeath/Hubspace-Homeassistant/issues/169))

- 5.3.0

  - Add support for Portable ACs ([#162](https://github.com/jdeath/Hubspace-Homeassistant/issues/162))
  - Update climate devices to adjust more closely to Hubspace
  - Fix an issue where Thermostats could incorrectly use Auto

- 5.2.3

  - Update linter to ruff

- 5.2.2

  - Fix battery percentage not showing ([#164](https://github.com/jdeath/Hubspace-Homeassistant/issues/164))

- 5.2.1

  - Fix Action calls from the UI

- 5.2.0

  - Fully implement exhaust fans ([#152](https://github.com/jdeath/Hubspace-Homeassistant/issues/152))

- 5.1.0

  - Permanently hide secrets within HA logs

- 5.0.0

  - BREAK: Binary Sensor names are more accurate but have new entity IDs
  - Implement climate / thermostats ([#143](https://github.com/jdeath/Hubspace-Homeassistant/issues/143))

- 4.6.0

  - Binary Sensor / Sensor is now identified on a per-resource basis, rather than root-device

- 4.5.0

  - Convert to aioafero==2.0.0
  - Update minimum version of HA to 2024.8 ([#149](https://github.com/jdeath/Hubspace-Homeassistant/issues/149))

- 4.4.2

  - Fixed an issue where the integration would create a new login to Hubspace each time it started

- 4.4.1

  - Fixed an issue where valves were labeled as fans
  - Fixed an issue where valves would not show the correct state

- 4.4.0

  - Implement reauth workflow
  - Gracefully handle issues with Hubspace API

- 4.3.0

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

- 4.2.0

  - Added supported for Glass Door control ([#127](https://github.com/jdeath/Hubspace-Homeassistant/issues/127))

- 4.1.1

  - Fix an issue where locks were not controllable ([#128](https://github.com/jdeath/Hubspace-Homeassistant/issues/128))

- 4.1.0

  - Re-implement the action / service send_command ([#94](https://github.com/jdeath/Hubspace-Homeassistant/issues/94))

- 4.0.1

  - Fixed an issue where fans could cause an UHE if they did not support
    some functionality ([#125](https://github.com/jdeath/Hubspace-Homeassistant/issues/125))

- 4.0.0

  - BREAK: Sensors have new names. Old sensors marked as unavailable can be removed.
  - Enabled customization of Hubspace polling intervals
  - Created a button for generating debug data dumps
  - Backend now uses aiohubspace to talk to Hubspace
  - Removed logic on setting states within Home Assistant
  - Devices are only created from the "top-level" device, rather than individually
  - Added models for HPDA110NWBP and HPSA11CWB

- 3.3.0

  - Add binary sensors for freezers

- 3.2.0

  - Enable a custom timeout during initial configuration

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

_Thanks to everyone who starred my repo! To star it click on the image below, then it will be on top right. Thanks!_

[![Star History Chart](https://api.star-history.com/svg?repos=jdeath/Hubspace-Homeassistant&type=Date)](https://star-history.com/#jdeath/Hubspace-Homeassistant&Date)
