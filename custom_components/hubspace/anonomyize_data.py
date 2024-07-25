import asyncio
import json
import logging
from dataclasses import asdict
from uuid import uuid4

from hubspace_async import HubSpaceConnection, HubSpaceDevice, HubSpaceState

logger = logging.getLogger(__name__)


FNAME_IND = 0


async def generate_anon_data(conn: HubSpaceConnection):
    devices = await conn.devices
    fake_devices = []
    parents = {}
    for dev in devices.values():
        fake_devices.append(anonymize_device(dev, parents))
    return fake_devices


def get_devices(conn: HubSpaceConnection) -> dict:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(conn.populate_data())
    return conn._devices


def generate_name(dev: HubSpaceDevice) -> str:
    return f"{dev.device_class}-{dev.model}"


def output_devices(conn: HubSpaceConnection):
    """Output all devices associated with the Account

    This should only be run when testing as it modified the
    log level.
    """
    devices = get_devices(conn)
    for child_id in devices:
        dev = devices[child_id]
        logger.info("Friendly Name: %s", dev.friendly_name)
        logger.info("\tDevice ID: %s", child_id)
        logger.info("\tParent ID: %s", dev.device_id)
        logger.info("\tDevice Class: %s", dev.device_class)


def anonymize_device_lookup(
    conn: HubSpaceConnection, friendly_name: str = None, child_id: str = None
):
    """Output anonymized device data for a device

    Lookup a device via friendly name or child_id and find all associated
    information. For example, a ceiling fan with a light will have
    three entries, one of the fan, one of the light, and one for the
    overall.
    """
    devices = get_devices(conn)
    matched_dev = None
    related = []
    # Find the device match
    for dev in devices.values():
        if friendly_name and dev.friendly_name != friendly_name:
            continue
        if child_id and dev.id != child_id:
            continue
        matched_dev = dev
        break
    if not matched_dev:
        raise RuntimeError("No matching device")
    related.append(matched_dev)
    if matched_dev.device_id:
        for dev in devices.values():
            if dev in related:
                continue
            if dev.device_id == matched_dev.device_id:
                related.append(dev)
    anon_data = []
    mapping = {}
    for dev in related:
        anon_data.append(anonymize_device(dev, mapping))
    identifier = f"{generate_name(related[0])}.json"
    with open(identifier, "w") as f:
        json.dump(anon_data, f, indent=4)
    return anon_data


def anonymize_device(dev: HubSpaceDevice, parent_mapping: dict):
    fake_dev = asdict(dev)
    global FNAME_IND
    # Modify the name
    fake_dev["friendly_name"] = f"friendly-device-{FNAME_IND}"
    FNAME_IND += 1
    # Modify the id
    fake_dev["id"] = str(uuid4())
    # Remove parent id
    parent = dev.device_id
    if parent not in parent_mapping:
        parent_mapping[parent] = str(uuid4())
    fake_dev["device_id"] = parent_mapping[parent]
    fake_dev["states"] = []
    for state in dev.states:
        fake_dev["states"].append(anonymize_state(state))
    return fake_dev


def anonymize_state(state: HubSpaceState):
    fake_state = asdict(state)
    fake_state["lastUpdateTime"] = 0
    if fake_state["functionClass"] == "wifi-ssid":
        fake_state["value"] = str(uuid4())
    elif isinstance(state.value, str):
        if "mac" in state.functionClass:
            fake_state["value"] = str(uuid4())
    return fake_state


def get_states(
    conn: HubSpaceConnection, friendly_name: str = None, child_id: str = None
):
    """Get all states associated to a specific ID"""
    states = []
    devices = get_devices(conn)
    for dev in devices.values():
        if friendly_name and dev.friendly_name != friendly_name:
            continue
        if child_id and dev.id != child_id:
            continue
        for state in dev.states:
            states.append(anonymize_state(state))
        with open(f"{generate_name(dev)}.json", "w") as f:
            json.dump(states, f, indent=4)
        return states


try:
    import click
    import hubspace_async

    user = click.option("--username", required=True, help="HubSpace Username")
    pwd = click.option("--password", required=True, help="HubSpace password")

    @click.group()
    @user
    @pwd
    @click.pass_context
    def cli(ctx, username, password):
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        ctx.ensure_object(dict)
        ctx.obj["conn"] = hubspace_async.HubSpaceConnection(username, password)

    @cli.command()
    @click.pass_context
    def get_devs(ctx):
        """Output all devices associated with the Account"""
        click.echo(output_devices(ctx.obj["conn"]))

    @cli.command()
    @click.option("--fn", required=True, help="Friendly Name")
    @click.pass_context
    def friendly_name(ctx, fn):
        """Output all devices associated to the name"""
        click.echo(anonymize_device_lookup(ctx.obj["conn"], friendly_name=fn))

    @cli.command()
    @click.option("--child_id", required=True, help="Child ID")
    @click.pass_context
    def child_id(ctx, child_id):
        """Output all devices associated to the child_id"""
        click.echo(anonymize_device_lookup(ctx.obj["conn"], child_id=child_id))

    @cli.command()
    @click.option("--child_id", required=True, help="Child ID")
    @click.pass_context
    def states(ctx, child_id):
        """Output all devices associated to the child_id"""
        click.echo(get_states(ctx.obj["conn"], child_id=child_id))

except:  # noqa
    pass

if __name__ == "__main__":
    cli()
