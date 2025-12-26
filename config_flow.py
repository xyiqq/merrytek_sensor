"""Config flow for Merrytek Sensor integration."""
from __future__ import annotations

import logging
import re
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_POLL_INTERVAL,
    CONF_DEVICE_ADDRESSES,
    CONF_SENSOR_TYPE,
    CONF_POLL_INTERVAL,
    SENSOR_TYPE_FMCW,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


def parse_addresses(address_str: str) -> list[int]:
    """Parse address string like '1,2,3' or '1-5' or '1,3-5,7' into list of integers."""
    addresses = []
    parts = address_str.replace(" ", "").split(",")
    
    for part in parts:
        if "-" in part:
            # Range like "1-5"
            match = re.match(r"(\d+)-(\d+)", part)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                addresses.extend(range(start, end + 1))
        else:
            # Single number
            if part.isdigit():
                addresses.append(int(part))
    
    # Filter valid range and remove duplicates
    addresses = sorted(set(addr for addr in addresses if 1 <= addr <= 247))
    return addresses


CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="迈睿感应器"): str,
        vol.Required(CONF_HOST, default="192.168.1.100"): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_DEVICE_ADDRESSES, default="1"): str,
        vol.Required(CONF_SENSOR_TYPE, default=SENSOR_TYPE_FMCW): vol.In(SENSOR_TYPES),
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=60.0)
        ),
    }
)


class MerrytekSensorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Merrytek Sensor."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        errors = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            host = user_input.get(CONF_HOST)
            port = user_input.get(CONF_PORT)
            address_str = user_input.get(CONF_DEVICE_ADDRESSES, "1")
            sensor_type = user_input.get(CONF_SENSOR_TYPE)

            # Parse addresses
            addresses = parse_addresses(address_str)
            
            if not addresses:
                errors["device_addresses"] = "invalid_addresses"
            else:
                # Create unique ID based on host:port
                uid = f"{host}_{port}"
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()

                # Store parsed addresses as list
                data = {
                    CONF_NAME: name,
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_DEVICE_ADDRESSES: addresses,  # Store as list
                    CONF_SENSOR_TYPE: sensor_type,
                    CONF_POLL_INTERVAL: user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                }

                type_name = SENSOR_TYPES.get(sensor_type, sensor_type)
                addr_display = ",".join(str(a) for a in addresses[:3])
                if len(addresses) > 3:
                    addr_display += f"...共{len(addresses)}个"
                
                return self.async_create_entry(
                    title=f"{name} ({type_name} 地址{addr_display})",
                    data=data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
            description_placeholders={
                "address_help": "支持格式: 1,2,3 或 1-5 或 1,3-5,7"
            }
        )
