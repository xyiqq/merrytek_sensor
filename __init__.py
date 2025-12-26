"""Merrytek Sensor integration for Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.const import Platform, CONF_PORT, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .gateway import MerrytekGateway
from .const import DOMAIN, CONF_DEVICE_ADDRESSES, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Merrytek Sensor integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Merrytek Sensor from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = config_entry.data.get(CONF_HOST)
    port = config_entry.data.get(CONF_PORT)
    device_addresses = config_entry.data.get(CONF_DEVICE_ADDRESSES, [1])
    poll_interval = config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    # Ensure addresses is a list
    if isinstance(device_addresses, int):
        device_addresses = [device_addresses]

    gateway = MerrytekGateway(hass, host, port, device_addresses, poll_interval)
    gateway.start()

    hass.data[DOMAIN][config_entry.entry_id] = gateway

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    gateway: MerrytekGateway = hass.data[DOMAIN].get(config_entry.entry_id)
    if gateway:
        gateway.stop()

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle removal of a config entry."""
    gateway: MerrytekGateway = hass.data[DOMAIN].get(config_entry.entry_id)
    if gateway:
        gateway.stop()
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
