### Installation

Supports most Light and Fan controls. Cloud polling updates the state every minute. Login may not be robust. May need to reset login/restart homeassistant if it hangs. Investigating usage of HASS's built-in OAuth support.

Copy this folder to `<config_dir>/custom_components/hubspace/`.

Add the following entry in your `configuration.yaml`:

```yaml
hubspace:
  username: your_hubspace_username (probably your email address)
  password: your_hubspace_password
```
