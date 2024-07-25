[![Stargazers repo roster for @jdeath/Hubspace-Homeassistant](https://git-lister.onrender.com/api/stars/jdeath/Hubspace-Homeassistant?limit=30)](https://github.com/jdeath/Hubspace-Homeassistant/stargazers)

Please ask support questions in homeassistant forums: https://community.home-assistant.io/t/add-support-for-hubspace-by-afero/306645

### Background
HubSpace is reliant on a cloud connection which means this integration could break at any point. Not all
devices may be supported with and developer time will be required to add new devices.

### Breaking Change:
Configuration is done through the `Add Integrations` rather than configuration.yaml.
Some devices may not work after moving the configuration to the integration. Please review
the docs on how to gather the device data. RGB Lights need additional work.

Now supports services for capability not provided by the integration. See Services section below

Thanks to @dloveall this release will automatically discover most devices. Specifying your friendlynames is still possible, but this now finds most models attached to your account. There may be some that are not auto discovered.

Since some of the internals were changed, so your light name may change. For instance, light.friendlyname might turn into light.friendlyname_2

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
After HubSpace has been added through HACs and Home Assistant has been removed, the
configuration continues within the UI like other integrations. First select `Settings`
on the navigation bar, then select `Devices & services`, ensure you are on the
`Integrations` tab, then finally select `ADD INTEGRATION` at the bottom right
of the page. Search for `HubSpace` and enter your username and password and
click `SUBMIT`. Entities should start appearing shortly after clicking submit.

If your username or password is incorrect, the form will not be submitted.

### Troubleshooting
If a device is not being automatically discovered, the device type may not be added to discovery. The following
device classes are supported:

 * fan
 * light
 * power-outlet
 * landscape-transformer (maybe)
 * water-valve

If your device class is not listed here, please refer to the section
``Support for a new model`` on how to get it added.

If a device is not responding to commands, enable debug through HA (Settings -> Devices & services ->
Integrations -> hubspace -> enable debug). This will enable debug logs for a developer to assist
with the problem. Please note that this debug logs could potentially show your account id
and device id.

### Support for a new model
To support a new model, the states and metadata will need to be gathered. To accomplish
this, you will need to gather the data. There are two ways to grab this information:

 * Through a shell (preferred, but some technical knowledge is required)
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
       python -m virtualenv "%userprofile%/.virtualenv/hubspace"
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
This is possible through the UI by navigating
to the integration and clicking "Enable debugging logging". After 30s or less,
the anonymized data will appear within the Home Assistant logs. Create a GitHub
issue with this information and it should be sufficient to add support.

[![Star History Chart](https://api.star-history.com/svg?repos=jdeath/Hubspace-Homeassistant&type=Date)](https://star-history.com/#jdeath/Hubspace-Homeassistant&Date)
