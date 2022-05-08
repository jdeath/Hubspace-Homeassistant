Major rewrite. Now it caches tokens for 118s and shares authentication for all lights, thus makes fewer API calls

Supports on/off for a couple types of light strips: 'AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232'

RGB working for: '50291, 50292'. No brigtness or White Colortemp yet

RGB (and maybe brightness) working for: '538551010, 538561010, 538552010, 538562010'

Light on/off: for '52133, 37833' fan. No brightness or fan control

On/Off,Brightness: PIR switch (HPDA311CWB)

Outlets (HPKA315CWB) work with on/off.

I would like to update to cloud push, but right now polls the state every minute by default (can be overwritten with scan_interval). Please contact me if good with websockets. The websocket system pushes bad data at first, which messses up the connection. I need a way to ignore that data.

Login may not be robust. May need to reset login/restart homeassistant if it hangs. Will add better logic later

Please make an issue if need support for a new model.

If you are having problems, first try renaming the device name in the App. This code fails with names like Office, Bedroom, Fireplace. Make it something unique and not the same as a group if having issues. Hopefully this has been fixed, but still could be issues.

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
