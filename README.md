### Installation

Copy this folder to `<config_dir>/custom_components/hubspace/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: hubspace
    username: your_hubspace_username (probably your email address)
    password: your_hubspace_password
    friendlynames:
      - 'LightName' (the name of your light as shown in the app)
