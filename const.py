"""Constants for Merrytek Sensor integration."""

DOMAIN = "merrytek_sensor"

# Default connection settings
DEFAULT_PORT = 8899
DEFAULT_ADDRESS = 1

# Modbus function codes
FUNC_READ_HOLDING_REGISTERS = 0x03
FUNC_WRITE_SINGLE_REGISTER = 0x06

# Register addresses (Merrytek sensors)
REG_STATUS = 0x0000           # Presence status (0=no person, 1=person detected)
REG_DELAY = 0x0001            # Delay time setting
REG_SENSITIVITY = 0x0002      # Sensitivity setting
REG_LIGHT_THRESHOLD = 0x0003  # Light threshold
REG_DEVICE_ADDRESS = 0x0004   # Device Modbus address

# Sensor types
SENSOR_TYPE_FMCW = "fmcw"     # MSA203D/MSA237D - Millimeter wave radar
SENSOR_TYPE_IR = "ir"         # MSA236D/MSA238D - Passive infrared

SENSOR_TYPES = {
    SENSOR_TYPE_FMCW: "FMCW 毫米波雷达 (MSA203D/MSA237D)",
    SENSOR_TYPE_IR: "红外 PIR (MSA236D/MSA238D)",
}

# Configuration keys
CONF_DEVICE_ADDRESSES = "device_addresses"  # List of Modbus addresses
CONF_SENSOR_TYPE = "sensor_type"
CONF_POLL_INTERVAL = "poll_interval"

# Default values
DEFAULT_POLL_INTERVAL = 1.0   # Poll every 1 second

# Reconnect interval (seconds)
RECONNECT_INTERVAL = 5

# CRC-16 Modbus polynomial (for manual calculation if needed)
CRC16_POLY = 0xA001
