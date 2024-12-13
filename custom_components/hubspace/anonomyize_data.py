__all__ = ["generate_anon_data", "generate_raw_data"]


import json
import logging
from dataclasses import asdict
from uuid import uuid4

import aiofiles
from hubspace_async import HubSpaceConnection, HubSpaceDevice, HubSpaceState

logger = logging.getLogger(__name__)


FNAME_IND = 0


async def generate_anon_data(conn: HubSpaceConnection, anon_name: bool=False,) -> dict:
    devices = await conn.devices
    fake_devices = []
    parents = await generate_parent_mapping(devices)
    device_links = {}
    for dev in devices.values():
        fake_devices.append(await anonymize_device(dev, parents, device_links, anon_name))
    return fake_devices


async def generate_raw_data(conn: HubSpaceConnection) -> dict:
    devices = await conn.devices
    fake_devs = []
    for dev in devices.values():
        fake_dev = asdict(dev)
        fake_dev["states"] = []
        for state in dev.states:
            fake_dev["states"].append(await anonymize_state(state, only_geo=True))
        fake_devs.append(fake_dev)
    return fake_devs


async def generate_parent_mapping(devices: list[HubSpaceDevice]) -> dict:
    mapping = {}
    for device in devices.values():
        if device.children:
            device.id = str(uuid4())
        new_children = []
        for child_id in device.children:
            new_uuid = str(uuid4())
            mapping[child_id] = {"parent": device.id, "new": new_uuid}
            new_children.append(new_uuid)
        device.children = new_children
    return mapping


async def get_devices(conn: HubSpaceConnection) -> dict:
    await conn.populate_data()
    return conn._devices


async def generate_name(dev: HubSpaceDevice) -> str:
    return f"{dev.device_class}-{dev.model}"


async def output_devices(conn: HubSpaceConnection):
    """Output all devices associated with the Account

    This should only be run when testing as it modified the
    log level.
    """
    devices = await get_devices(conn)
    for child_id in devices:
        dev = devices[child_id]
        logger.info("Friendly Name: %s", dev.friendly_name)
        logger.info("\tDevice ID: %s", child_id)
        logger.info("\tParent ID: %s", dev.device_id)
        logger.info("\tDevice Class: %s", dev.device_class)


async def anonymize_device_lookup(
    conn: HubSpaceConnection, friendly_name: str = None, child_id: str = None, anon_name: bool = False,
):
    """Output anonymized device data for a device

    Lookup a device via friendly name or child_id and find all associated
    information. For example, a ceiling fan with a light will have
    three entries, one of the fan, one of the light, and one for the
    overall.
    """
    devices = await get_devices(conn)
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
    parents = await generate_parent_mapping(devices)
    device_links = {}
    for dev in related:
        anon_data.append(await anonymize_device(dev, parents, device_links, anon_name))
    identifier = f"dump_{await generate_name(related[0])}.json"
    async with aiofiles.open(identifier, "w") as f:
        await f.write(json.dumps(anon_data, indent=4))
    return anon_data


async def anonymize_device(
    dev: HubSpaceDevice, parent_mapping: dict, device_links: dict, anon_name,
):
    fake_dev = asdict(dev)
    if anon_name:
        global FNAME_IND
        # Modify the name
        fake_dev["friendly_name"] = f"friendly-device-{FNAME_IND}"
        FNAME_IND += 1
    # Modify the id
    if dev.id in parent_mapping:
        fake_dev["id"] = parent_mapping[dev.id]["new"]
    else:
        fake_dev["id"] = str(uuid4())
    # Generate a custom device_id link
    dev_link = dev.device_id
    if dev_link not in device_links:
        device_links[dev_link] = str(uuid4())
    fake_dev["device_id"] = device_links[dev_link]
    fake_dev["states"] = []
    for state in dev.states:
        fake_dev["states"].append(await anonymize_state(state))
    return fake_dev


async def anonymize_state(state: HubSpaceState, only_geo: bool = False):
    fake_state = asdict(state)
    fake_state["lastUpdateTime"] = 0
    if fake_state["functionClass"] == "geo-coordinates":
        fake_state["value"] = {"geo-coordinates": {"latitude": "0", "longitude": "0"}}
    elif not only_geo:
        if fake_state["functionClass"] == "wifi-ssid":
            fake_state["value"] = str(uuid4())
        elif isinstance(state.value, str):
            if "mac" in state.functionClass:
                fake_state["value"] = str(uuid4())
    return fake_state


async def get_states(
    conn: HubSpaceConnection, friendly_name: str = None, child_id: str = None
):
    """Get all states associated to a specific ID"""
    states = []
    devices = await get_devices(conn)
    for dev in devices.values():
        if friendly_name and dev.friendly_name != friendly_name:
            continue
        if child_id and dev.id != child_id:
            continue
        for state in dev.states:
            states.append(await anonymize_state(state))
        async with aiofiles.open(f"dump_{await generate_name(dev)}.json", "w") as f:
            await f.write(json.dumps(states, indent=4))
        return states


try:
    import asyncclick as click
    import hubspace_async

    user = click.option("--username", required=True, help="HubSpace Username")
    pwd = click.option("--password", required=True, help="HubSpace password")
    aname = click.option("--anon-name", default=False, help="Anonymize name")

    @click.group()
    @user
    @pwd
    @click.pass_context
    async def cli(ctx, username, password):
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        ctx.ensure_object(dict)
        ctx.obj["conn"] = hubspace_async.HubSpaceConnection(username, password)

    @cli.command()
    @click.pass_context
    async def get_devs(ctx):
        """Output all devices associated with the Account"""
        click.echo(await output_devices(ctx.obj["conn"]))

    @cli.command()
    @click.option("--fn", required=True, help="Friendly Name")
    @aname
    @click.pass_context
    async def friendly_name(ctx, fn, anon_name):
        """Output all devices associated to the name"""
        click.echo(await anonymize_device_lookup(ctx.obj["conn"], friendly_name=fn, anon_name=anon_name))

    @cli.command()
    @click.option("--child_id", required=True, help="Child ID")
    @aname
    @click.pass_context
    async def child_id(ctx, child_id, anon_name):
        """Output all devices associated to the child_id"""
        click.echo(await anonymize_device_lookup(ctx.obj["conn"], child_id=child_id, anon_name=anon_name))

    @cli.command()
    @click.option("--child_id", required=True, help="Child ID")
    @click.pass_context
    async def states(ctx, child_id):
        """Output all devices associated to the child_id"""
        click.echo(await get_states(ctx.obj["conn"], child_id=child_id))

    @cli.command()
    @click.pass_context
    async def raw_data(ctx):
        """Get the raw output. This data is not anonymized"""
        await get_devices(ctx.obj["conn"])
        async with aiofiles.open("dump_raw-data.json", "w") as f:
            data = await generate_raw_data(ctx.obj["conn"])
            await f.write(json.dumps(data, indent=4))

    @cli.command()
    @aname
    @click.pass_context
    async def anon_data(ctx, anon_name):
        """Get the raw output. This data is not anonymized"""
        async with aiofiles.open("dump_anon-data.json", "w") as f:
            data = await generate_anon_data(ctx.obj["conn"], anon_name=anon_name)
            await f.write(json.dumps(data, indent=4))

except:  # noqa
    pass

if __name__ == "__main__":
    try:
        cli()
    except NameError:
        logger.exception("Click is not installed")
