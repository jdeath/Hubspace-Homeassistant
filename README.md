# Overview
This repository provides an integration between Hubspace and Home Assistant. Due to the cloud-first
nature of Hubspace devices, an internet connection needs to be available, along with the Hubspace servers.

Please ask support questions in homeassistant forums: https://community.home-assistant.io/t/add-support-for-hubspace-by-afero/306645

## Supported Devices
A supported device indicates that is maps into Home Assistant. Please note that not all
devices will correctly map and may require further troubleshooting. The supported Devices
are as follows:

 * Fan

   * On/Off
   * Speed
   * Preset mode

 * Freezer

   * Error sensors

 * Lock

   * Lock / Unlock

 * Light

   * On/Off
   * Color Temperature
   * Color Sequences
   * Dimming
   * RGB

 * Outlet / Switch / Transformer

   * On/Off

 * Water Valve

   * Open / Close


## Changelog

 * 4.0.1

   * Fixed an issue where fans could cause an UHE if they did not support
     some functionality

 * 4.0.0

   * BREAK: Sensors have new names. Old sensors marked as unavailable can be removed.
   * Enabled customization of Hubspace polling intervals
   * Created a button for generating debug data dumps
   * Backend now uses aiohubspace to talk to Hubspace
   * Removed logic on setting states within Home Assistant
   * Devices are only created from the "top-level" device, rather than individually
   * Added models for HPDA110NWBP and HPSA11CWB

 * 3.3.0

   * Add binary sensors for freezers

 * 3.2.0

   * Enable a custom timeout during initial configuration


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

 * Unable to authenticate with the provided credentials

   * Ensure the provided credentials can authenticate to Hubspace

 * Connection timed out when reaching the server

   * Increase the timeout



# Troubleshooting
Device troubleshooting may require a data dump from Hubspace. This can
be generated within the UI, but will need to be retrieved with something
that can access Home Assistants Filestore.

 * Navigate to the Hubspace Devices

   * Settings -> Devices & services -> Integrations -> Hubspace

 * Click on devices on the navigation bar underneath the Hubspace logo
 * Click on the device named labeled `hubspace-<email_address>`
 * Click `Press` on `Generate Debug` underneath Controls
 * Open File Editor
 * Click the folder icon on the top left
 * Navigate to custom_components -> hubspace
 * Download the required files:

   * `_dump_hs_devices.json`: Anonymized device dumps consumed by the Hubspace integration


# FAQ

 * I have a device in Hubspace that is not added to Home Assistant

   * Check the logs for any warning / errors around hubspace and report the issue.
   * If no warning / error messages exist around Hubspace, the device type is likely
     not supported. Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that did not discover

 * I have a device and its missing functionality

   * Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that is not working
     along with the broken functionality

 * I have a device and its functionality is not working

   * Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that is not working
     along with the broken functionality
   * If the developers are unable to solve the problem with the anonymized data,
     the raw data may need to be provided

 * I have a device that does not display the correct model

   * Generate the debug logs and create an issue on GitHub.



_Thanks to everyone who starred my repo! To star it click on the image below, then it will be on top right. Thanks!_

[![Star History Chart](https://api.star-history.com/svg?repos=jdeath/Hubspace-Homeassistant&type=Date)](https://star-history.com/#jdeath/Hubspace-Homeassistant&Date)
