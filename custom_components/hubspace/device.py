"""Handles Hubspace top-level `device` mapping to Home Assistant device."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohubspace.v1 import HubspaceBridgeV1
from aiohubspace.v1.controllers.device import DeviceController
from aiohubspace.v1.controllers.event import EventType
from aiohubspace.v1.models.device import Device
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

if TYPE_CHECKING:
    from .bridge import HubspaceBridge


async def async_setup_devices(bridge: HubspaceBridge):
    """Manage setup of devices"""
    entry = bridge.config_entry
    hass = bridge.hass
    api: HubspaceBridgeV1 = bridge.api  # to satisfy typing
    dev_reg = dr.async_get(hass)
    dev_controller: DeviceController = api.devices

    @callback
    def add_device(hs_device: Device) -> dr.DeviceEntry:
        """Register a Hubspace device in device registry."""
        connections = []
        if hs_device.device_information.wifi_mac:
            connections.append(
                (dr.CONNECTION_NETWORK_MAC, hs_device.device_information.wifi_mac)
            )
        if hs_device.device_information.ble_mac:
            connections.append(
                (dr.CONNECTION_BLUETOOTH, hs_device.device_information.ble_mac)
            )
        return dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, hs_device.device_information.parent_id)},
            name=hs_device.device_information.name,
            model=hs_device.device_information.model
            or hs_device.device_information.default_name,
            manufacturer=hs_device.device_information.manufacturer,
            connections=connections,
        )

    @callback
    def remove_device(device_id: str) -> None:
        """Remove device from registry."""
        if device := dev_reg.async_get_device(identifiers={(DOMAIN, device_id)}):
            # note: removal of any underlying entities is handled by core
            dev_reg.async_remove_device(device.id)

    @callback
    def handle_device_event(evt_type: EventType, hs_device: Device) -> None:
        """Handle event from Device controller."""
        if evt_type == EventType.RESOURCE_DELETED:
            remove_device(hs_device.device_information.parent_id)
        elif evt_type == EventType.RESOURCE_ADDED:
            add_device(hs_device)

    # create/update all current devices found in controllers
    known_devices = [add_device(hs_device) for hs_device in dev_controller]

    # Check for nodes that no longer exist and remove them
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if device not in known_devices:
            dev_reg.async_remove_device(device.id)

    # add listener for updates on Hubspace controllers
    entry.async_on_unload(dev_controller.subscribe(handle_device_event))
