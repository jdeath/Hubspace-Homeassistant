### Installation

Only supports on/off right now. I would like to update to cloud push, but right now it updates state every minute. Login may not be robust. May need to reset login/restart homeassistant if it hangs. Will add better logic later. Lights in the hubspace app should not have spaces, or integration will have issues

Copy this folder to `<config_dir>/custom_components/hubspace/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: hubspace
    username: your_hubspace_username (probably your email address)
    password: your_hubspace_password
    debug: true (use this if want debug output, if you have an unsupported light)
    friendlynames:
      - 'BoysRoom' (the name of your light as shown in the app, rename so don't have spaces in light name)
      - 'GirlsRoom' (the name of your light as shown in the app,rename so don't have spaces in light name)
