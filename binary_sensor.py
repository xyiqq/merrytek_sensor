"""Binary sensor platform for Merrytek Sensor."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_SENSOR_TYPE, SENSOR_TYPES, SENSOR_TYPE_FMCW, CONF_DEVICE_ADDRESSES
from .gateway import MerrytekGateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Merrytek binary sensors."""
    gateway: MerrytekGateway = hass.data[DOMAIN][config_entry.entry_id]
    sensor_type = config_entry.data.get(CONF_SENSOR_TYPE, SENSOR_TYPE_FMCW)
    device_addresses = config_entry.data.get(CONF_DEVICE_ADDRESSES, [1])
    
    # Ensure addresses is a list
    if isinstance(device_addresses, int):
        device_addresses = [device_addresses]

    sensors = []

    # Add online sensor (one for the gateway)
    sensors.append(MerrytekOnlineSensor(gateway, config_entry.entry_id))

    # Add presence sensor for each device address
    for addr in device_addresses:
        sensors.append(MerrytekPresenceSensor(
            gateway, config_entry.entry_id, addr, sensor_type
        ))

    async_add_entities(sensors)


class MerrytekPresenceSensor(BinarySensorEntity):
    """Representation of Merrytek presence detection sensor."""

    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self, 
        gateway: MerrytekGateway, 
        entry_id: str,
        device_address: int,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        self._gateway = gateway
        self._entry_id = entry_id
        self._device_address = device_address
        self._sensor_type = sensor_type

        type_name = SENSOR_TYPES.get(sensor_type, sensor_type)
        self._attr_name = f"迈睿感应器 地址{device_address} 存在检测"
        self._attr_unique_id = f"{entry_id}_presence_{device_address}"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        self._attr_is_on = self._gateway.get_presence_state(self._device_address)
        self._gateway.register_presence_callback(self._device_address, self._handle_presence_update)

    def _handle_presence_update(self, state: bool) -> None:
        """Handle presence state update."""
        self._attr_is_on = state
        self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._gateway.online_state


class MerrytekOnlineSensor(BinarySensorEntity):
    """Representation of Merrytek sensor connection status."""

    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, gateway: MerrytekGateway, entry_id: str) -> None:
        """Initialize the sensor."""
        self._gateway = gateway
        self._entry_id = entry_id
        self._attr_name = "迈睿感应器 在线状态"
        self._attr_unique_id = f"{entry_id}_online"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        self._attr_is_on = self._gateway.online_state
        self._gateway.online_callbacks.append(self._handle_online_update)

    def _handle_online_update(self, state: bool) -> None:
        """Handle online state update."""
        self._attr_is_on = state
        self.schedule_update_ha_state()
