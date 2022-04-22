Major rewrite. Now it caches tokens for 120s and shares authentication for all lights, thus makes fewer API call
Supports on/off for a couple types of light strips: 'AL-TP-RGBCW-60-2116, AL-TP-RGBCW-60-2232'
Trying to get RGB working for: '50291, 50292' , but probably does not work yet. If want to revert to on/off, just edit line 97 to have a made up model name

Only supports on/off right now except for the PIR switch, which supports brightness. I would like to update to cloud push, but right now it updates state every minute. Login may not be robust. May need to reset login/restart homeassistant if it hangs. Will add better logic later

### Installation


copy this folder to `<config_dir>/custom_components/hubspace/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: hubspace
    username: your_hubspace_username (probably your email address)
    password: your_hubspace_password
    debug: true (use this if want debug output, if you have an unsupported light, set false if not needed)
    friendlynames:
      - 'BoysRoom' (the name of your light as shown in the app)
      - 'GirlsRoom' (the name of your light as shown in the app)
