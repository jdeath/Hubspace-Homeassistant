
Only supports on/off right now. I would like to update to cloud push, but right now it updates state every minute. Login may not be robust. May need to reset login/restart homeassistant if it hangs. Will add better logic later

### Installation

Add this repository to HACS: https://github.com/jdeath/Hubspace-Homeassistant

Or, copy this folder to `<config_dir>/custom_components/hubspace/`.
Don't need to do both

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: hubspace
    username: your_hubspace_username (probably your email address)
    password: your_hubspace_password
    friendlynames:
      - 'BoysRoom' (the name of your light as shown in the app)
      - 'GirlsRoom' (the name of your light as shown in the app)
