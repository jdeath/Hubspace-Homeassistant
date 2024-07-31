[![Stargazers repo roster for @jdeath/Hubspace-Homeassistant](https://git-lister.onrender.com/api/stars/jdeath/Hubspace-Homeassistant?limit=30)](https://github.com/jdeath/Hubspace-Homeassistant/stargazers)

Please ask support questions in homeassistant forums: https://community.home-assistant.io/t/add-support-for-hubspace-by-afero/306645

### Background
HubSpace is reliant on a cloud connection which means this integration could break at any point. Not all
devices may be supported with and developer time will be required to add new devices. Supported
device types:

 * fan
   * On/Off
   * Speed
   * Preset mode
 * device-lock
   * Lock / Unlock
 * light
   * On/Off
   * Color Temperature
   * Color Sequences
   * Dimming
   * RGB
   * Not working
     * HS (missing data dump for this device)
     * RGBW (missing data dump for this device)
     * RGBWW (missing data dump for this device)
     * WHITE (missing data dump for this device)
     * XY (missing data dump for this device)
 * power-outlet
   * On/Off
   * Not working
     * Power Monitoring (Missing data dumps for this information)
 * switch
   * On/Off
 * landscape-transformer (missing data dump for this device)
   * On/Off
 * water-valve
   * Open / Close

### Breaking Change:
@Expl0dingBanana did amazing work to allow configuration via the UI, async calls, robust autoscan, and treating devices correctly instead of everything as a light. A few devices are left to be tested.

Configuration is done through the `Add Integrations` rather than configuration.yaml.
Some devices may not work after moving the configuration to the integration. Please review
the docs on how to gather the device data to send to the developer. 

Now supports services for capability not provided by the integration. See Services section below

Thanks to @dloveall and now @Expl0dingBanana this release will automatically discover most devices. Post an issue, if your device is no longer found.

Since some of the internals were changed, so your light name may change. locks will now be locks, fans actual fans, etc 

To solve this, go to Settings->Devices and Services->Entities
find the light.friendlyname and delete it. then find the light.friendlyname_2 and rename it light.friendlyname

### Information :
This integration talks to the HubSpace API to set and retrieve states for all
of your registered devices. After performing the configuration, it will
register all devices unless specified by `friendlyNames` and/or `roomNames`. Once
the devices are discovered, it will determine device capability and show
correctly within Home Assistant.

_Thanks to everyone who starred my repo! To star it click on the image below, then it will be on top right. Thanks!_

[![Stargazers repo roster for @jdeath/Hubspace-Homeassistant](https://reporoster.com/stars/jdeath/Hubspace-Homeassistant)](https://github.com/jdeath/hubspace-homeassistant/stargazers)

### Installation


#### UI (Preferred)
Add this repo as a custom repository in [HACS](https://hacs.xyz/). Add the hubspace integration.

Clicking this badge should add the repo for you:
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jdeath&repository=Hubspace-Homeassistant&category=integration)

#### Manual
Manually add repo:
Adding a custom repo directions `https://hacs.xyz/docs/faq/custom_repositories/`
Use the custom repo link `https://github.com/jdeath/Hubspace-Homeassistant`
Select the category type `integration`
Then once it's there (still in HACS) click the INSTALL button

Manual method: copy the hubspace/ folder in the repo to `<config_dir>/custom_components/hubspace/`.

### Configuration
After HubSpace has been added through HACs, the
configuration continues within the UI like other integrations. First select `Settings`
on the navigation bar, then select `Devices & services`, ensure you are on the
`Integrations` tab, then finally select `ADD INTEGRATION` at the bottom right
of the page. Search for `HubSpace` and enter your username and password and
click `SUBMIT`. Entities should start appearing shortly after clicking submit.

If your username or password is incorrect, the form will not be submitted.

### Troubleshooting

 * I have a device in HubSpace that is not added to Home Assistant
   * Check the logs for any warning / errors around hubspace and report the issue.
   * If no warning / error messages exist around HubSpace, the device type is likely
     not supported. Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state thedevice that did not discover
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

### Support for a new model
To support a new model, the states and metadata will need to be gathered. To accomplish
this, you will need to gather the data. There are two ways to grab this information:

 * Through a shell (target a specific device)
 * Through the UI

#### Shell
Gathering this information through the shell is preferred as you
can target the device you want. You must have a python
interpreter installed for this to work. After it is installed,
the following setup steps must be run:

 * (Optional) Use a virtualenv
   * Unix
     * ```bash
       python -m pip install virtualenv
       python -m virtualenv ~/.virtualenv/hubspace
       source ~/.virtualenv/hubspace/bin/activate
       ```
   * Windows
     * ```bat
       python -m pip install virtualenv
       python -m virtualenv "%userprofile%\.virtualenv\hubspace"
       %userprofile%\.virtualenv\hubspace\Scripts\activate.bat
       ```
 * Download requirements
   * ```sh
     python -m pip install requests "hubspace_async>=0.0.5" click
     ```
 * Goto your home directory
   * Unix
     * ```bash
       cd ~
       ```
   * Windows
     * ```bat
       cd  %userprofile%
       ```
 * Download the anonymizer code
   * ```bash
     python -c "import requests; data=requests.get('https://raw.githubusercontent.com/Expl0dingBanana/Hubspace-Homeassistant/rework-tmp/custom_components/hubspace/anonomyize_data.py').text; fh=open('anonomyize_data.py', 'w'); fh.write(data); fh.close();"
     ```
 * Run the anonymizer code (but fill in username and password)
   * Determine the device (gets child_id and friendly names)
     * Get all devices
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" get-devs
         ```
   * Gather data based on friendlyName or childID. This will create a .json file with the friendlyname in the current directory
     * Get devices based on a friendlyName
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" friendly-name --fn "<friendly name>"
         ```
     * Get devices based on a childId
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" child-id --child_id "<child_id>"
         ```

#### Through the UI
Gathering data through the UI provides a less targeted approach to gathering data
as it will pull all devices. This may be required if a device cannot be fixed with
a normal data dump or you are not comfortable running python on your system. It requires
the add-on `File Editor` or a similar add-on /  integration that enables you to download
files from Home Assistant. After  the file downloader has been installed onto Home
Assistant, the following steps are required to gather the data:

 * Enable Debug
   * Settings -> Devices & services -> Integrations -> hubspace -> Enable debug logging
 * Wait 30s - 60s for the files to generate
 * Open File Editor
 * Click the folder icon on the top left
 * Navigate to custom_components -> hubspace
 * Download the required files:
   * `_dump_hs_devices.json`: Anonymized device dumps consumed by the HubSpace integration
   * `_dump_hs_raw.json`: Raw data from the connector. This data is not anonymized
 * Disable debug
   * Settings -> Devices & services -> Integrations -> hubspace -> Disable debug logging

[![Star History Chart](https://api.star-history.com/svg?repos=jdeath/Hubspace-Homeassistant&type=Date)](https://star-history.com/#jdeath/Hubspace-Homeassistant&Date)
