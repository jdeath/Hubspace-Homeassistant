Major rewrite. Now it caches tokens for 118s and shares authentication for all lights, thus makes fewer API calls

Supports on/off for a couple types of light strips: 'AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232'

RGB working for: '50291, 50292'. No brigtness or White Colortemp yet

RGB (and maybe brightness) working for: '538551010, 538561010, 538552010, 538562010'

Light on/off/dim and fan on/off/low/med/high/full for '52133, 37833' fan. Fan speed is controlled like a light dimmer.

On/Off,Brightness: PIR switch (HPDA311CWB)

Outlets (HPKA315CWB) work with on/off on both outputs.

Landscape Transformer works with on/off on all 3 outputs. System-wide Watts and voltage available as attribute in first output entity

I would like to update to cloud push, but right now polls the state every minute by default (can be overwritten with scan_interval). Please contact me if good with websockets. The websocket system pushes bad data at first, which messses up the connection. I need a way to ignore that data.

_Thanks to everyone having starred my repo! To star it click on the image below, then it will be on top right. Thanks!_

[![Stargazers repo roster for @jdeath/Hubspace-Homeassistant](https://reporoster.com/stars/jdeath/Hubspace-Homeassistant)](https://github.com/jdeath/hubspace-homeassistant/stargazers)

### Installation

copy this folder to `<config_dir>/custom_components/hubspace/`.

Add the following entry in your `configuration.yaml`:

Do *not* name your lights in the app the same as a room you have defined or the logic will get tripped up: Office, Bedroom, etc   

```yaml
light:
  - platform: hubspace
    username: your_hubspace_username (probably your email address)
    password: your_hubspace_password
    debug: true (use this if want debug output, if you have an unsupported light, set false if not needed)
    friendlynames:
      - 'BoysRoom' (the name of your light as shown in the app)
      - 'GirlsRoom' (the name of your light as shown in the app)
```


### Troubleshooting
If you are having problems, first try renaming the device name in the App. Do not use spaces in the name of your lights. This code may also fail with names like Office, Bedroom, Fireplace. Make it something unique and not the same as a group. Hopefully this has been fixed, but still could be issues.

Also be sure to check the friendlyname of your light. It must match *exactly* as shown in the app, including uppercase/lowercase. Requiring the case to match may be a recent change by Hubspace

### Support for a new model
Please make an issue if want support for a new model. I will need your help to test. Get the item loaded in homeassistant as above. Set debug:true in configuration as shown above. Click on the entity in homeassistant, expand the attributes, and send me the model and debug fields. Best to PM me these on the homeassistant forums, as there is semi-private information in them. Send me these fields with the light set to on/off/etc (you may need to use the app). If that doesn't work, I may need better debug logs. Then you can add in your configuration.yaml (not in the hubspace section). Then you email me your homassistant.log 
```
logger:
  default: error
  logs:
    custom_components.hubspace: debug

```
you may already have the top two lines, just need to add the buttom two

### Fan Support
Since the fan is implimented as a light with a dimmer, you can use a template to make it appear as a fan. From a user:
```
# Example configuration.yaml entry
fan:
  - platform: template
    fans:
      living_room_fan::
        friendly_name: "Fan"
        value_template: "{{ states('light.ceilingfan_fan') }}"
        percentage_template: "{{ (state_attr('light.ceilingfan_fan', 'brightness') / 255 * 100) | int }}"
        turn_on:
          service: homeassistant.turn_on
          entity_id: light.ceilingfan_fan
        turn_off:
          service: homeassistant.turn_off
          entity_id: light.ceilingfan_fan
        set_percentage:
          service: light.turn_on
          entity_id: light.ceilingfan_fan
          data_template:
            brightness: "{{ ( percentage / 100 * 255) | int }}"
        speed_count: 4
        
```

### Transformer Support
System-wide watt and voltage setting available as attribute in the first output entity. Get watts in lovelace with a card with this entry:
```
- entity: Friendlyname_transformer_1
  type: attribute
  attribute: watts
  ```
