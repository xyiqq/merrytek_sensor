"""TCP/Modbus RTU Gateway for Merrytek Sensors."""
from __future__ import annotations

import asyncio
import logging
from asyncio import Transport, Protocol, Task, Queue
from typing import Callable

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_POLL_INTERVAL,
    RECONNECT_INTERVAL,
    FUNC_READ_HOLDING_REGISTERS,
    REG_STATUS,
)

_LOGGER = logging.getLogger(__name__)


def calculate_crc16(data: bytes) -> int:
    """Calculate Modbus CRC-16."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class MerrytekTCPClient(Protocol):
    """TCP Client Protocol for Merrytek sensors over Modbus RTU."""

    def __init__(self, on_conn_cb: Callable, on_receive_cb: Callable) -> None:
        self._on_conn_cb = on_conn_cb
        self._on_receive_cb = on_receive_cb
        self._buffer = bytearray()

    def connection_made(self, transport: Transport) -> None:
        self._on_conn_cb(True)

    def connection_lost(self, exc: Exception | None) -> None:
        self._on_conn_cb(False)

    def data_received(self, data: bytes) -> None:
        """Handle received data with Modbus RTU frame parsing."""
        self._buffer.extend(data)
        _LOGGER.debug("Received raw data: %s", data.hex())
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process buffer to extract complete Modbus RTU frames."""
        while len(self._buffer) >= 5:
            func_code = self._buffer[1] if len(self._buffer) > 1 else 0
            
            if func_code == FUNC_READ_HOLDING_REGISTERS:
                if len(self._buffer) < 3:
                    break
                byte_count = self._buffer[2]
                expected_len = 3 + byte_count + 2
                
                if len(self._buffer) >= expected_len:
                    frame = bytes(self._buffer[:expected_len])
                    self._buffer = self._buffer[expected_len:]
                    
                    if self._verify_crc(frame):
                        self._on_receive_cb(frame)
                    else:
                        _LOGGER.warning("CRC error in frame: %s", frame.hex())
                else:
                    break
            elif func_code & 0x80:
                if len(self._buffer) >= 5:
                    frame = bytes(self._buffer[:5])
                    self._buffer = self._buffer[5:]
                    _LOGGER.warning("Modbus error response: %s", frame.hex())
                else:
                    break
            else:
                _LOGGER.debug("Skipping unknown byte: %02x", self._buffer[0])
                self._buffer.pop(0)

    def _verify_crc(self, frame: bytes) -> bool:
        """Verify CRC-16 of a Modbus RTU frame."""
        if len(frame) < 4:
            return False
        data = frame[:-2]
        received_crc = frame[-2] | (frame[-1] << 8)
        calculated_crc = calculate_crc16(data)
        return received_crc == calculated_crc

    def eof_received(self) -> None:
        _LOGGER.debug("EOF received from server")


class MerrytekGateway:
    """Gateway for Merrytek sensor communication over TCP/Modbus RTU.
    
    Supports multiple device addresses on the same TCP connection.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        device_addresses: list[int],
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Initialize the gateway."""
        self._hass = hass
        self._host = host
        self._port = port
        self._device_addresses = device_addresses
        self._poll_interval = poll_interval

        self._transport: Transport | None = None
        self._protocol: MerrytekTCPClient | None = None
        self._running = False

        # Connection state
        self._connected = False
        self._online_state = False

        # Sensor states: {address: presence_state}
        self._presence_states: dict[int, bool] = {addr: False for addr in device_addresses}

        # Current polling index
        self._poll_index = 0

        # Background tasks
        self._poll_task: Task | None = None
        self._conn_task: Task | None = None

        # TX queue
        self._tx_queue: Queue = Queue(maxsize=64)
        self._tx_task: Task | None = None

        # Callbacks
        self.online_callbacks: list[Callable[[bool], None]] = []
        # Presence callbacks: {address: [callbacks]}
        self.presence_callbacks: dict[int, list[Callable[[bool], None]]] = {
            addr: [] for addr in device_addresses
        }

    @property
    def online_state(self) -> bool:
        """Return online state."""
        return self._online_state

    @property
    def device_addresses(self) -> list[int]:
        """Return list of device addresses."""
        return self._device_addresses

    def get_presence_state(self, address: int) -> bool:
        """Get presence state for a specific address."""
        return self._presence_states.get(address, False)

    def register_presence_callback(self, address: int, callback: Callable[[bool], None]) -> None:
        """Register a presence callback for a specific address."""
        if address in self.presence_callbacks:
            self.presence_callbacks[address].append(callback)

    def _build_read_registers_command(self, device_address: int, start_reg: int, count: int = 1) -> bytes:
        """Build a Modbus RTU read holding registers command."""
        data = bytes([
            device_address,
            FUNC_READ_HOLDING_REGISTERS,
            (start_reg >> 8) & 0xFF,
            start_reg & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ])
        crc = calculate_crc16(data)
        return data + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    def read_presence_status(self, device_address: int) -> None:
        """Queue a read command for presence status register."""
        cmd = self._build_read_registers_command(device_address, REG_STATUS, 1)
        try:
            self._tx_queue.put_nowait(cmd)
        except asyncio.QueueFull:
            _LOGGER.warning("TX queue full, dropping command")

    def _on_connection_state(self, state: bool) -> None:
        """Handle connection state changes."""
        self._connected = state
        self._online_state = state
        _LOGGER.info("Connection state: %s", "connected" if state else "disconnected")
        for callback in self.online_callbacks:
            callback(state)

    def _on_frame_received(self, frame: bytes) -> None:
        """Handle received Modbus RTU frame."""
        _LOGGER.debug("Received valid frame: %s", frame.hex())
        
        if len(frame) < 5:
            return

        addr = frame[0]
        func = frame[1]

        # Check if this is one of our devices
        if addr not in self._device_addresses:
            _LOGGER.debug("Frame from unknown device address: %d", addr)
            return

        if func == FUNC_READ_HOLDING_REGISTERS:
            byte_count = frame[2]
            if byte_count >= 2:
                reg_value = (frame[3] << 8) | frame[4]
                new_presence = reg_value != 0
                
                old_presence = self._presence_states.get(addr, False)
                if new_presence != old_presence:
                    self._presence_states[addr] = new_presence
                    _LOGGER.info("Address %d presence state changed: %s", 
                                addr, "detected" if new_presence else "clear")
                    for callback in self.presence_callbacks.get(addr, []):
                        callback(new_presence)

    async def _create_connection(self) -> bool:
        """Create TCP connection."""
        try:
            loop = asyncio.get_event_loop()
            self._transport, self._protocol = await loop.create_connection(
                lambda: MerrytekTCPClient(
                    self._on_connection_state,
                    self._on_frame_received
                ),
                self._host,
                self._port,
            )
            _LOGGER.info("Connected to %s:%d", self._host, self._port)
            return True
        except Exception as e:
            _LOGGER.error("Connection failed: %s", e)
            self._on_connection_state(False)
            return False

    def _send_data(self, data: bytes) -> None:
        """Send data through transport."""
        if self._transport and self._connected:
            _LOGGER.debug("Sending: %s", data.hex())
            self._transport.write(data)

    async def _tx_loop(self) -> None:
        """Process TX queue."""
        while self._running:
            try:
                data = await asyncio.wait_for(
                    self._tx_queue.get(), timeout=1.0
                )
                self._send_data(data)
                await asyncio.sleep(0.05)  # 50ms delay between commands
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                _LOGGER.error("TX loop error: %s", e)

    async def _poll_loop(self) -> None:
        """Poll presence status for all devices in round-robin."""
        while self._running:
            if self._connected and self._device_addresses:
                # Poll next device in sequence
                addr = self._device_addresses[self._poll_index]
                self.read_presence_status(addr)
                
                # Move to next device
                self._poll_index = (self._poll_index + 1) % len(self._device_addresses)
                
                # Calculate delay to maintain overall poll interval
                per_device_delay = self._poll_interval / len(self._device_addresses)
                await asyncio.sleep(max(per_device_delay, 0.1))
            else:
                await asyncio.sleep(self._poll_interval)

    async def _check_conn_loop(self) -> None:
        """Check and maintain connection."""
        while self._running:
            if not self._connected:
                _LOGGER.info("Attempting to reconnect...")
                await self._create_connection()
            await asyncio.sleep(RECONNECT_INTERVAL)

    def start(self) -> None:
        """Start the gateway."""
        if self._running:
            return

        self._running = True
        _LOGGER.info("Starting Merrytek gateway for %s:%d with %d devices: %s",
                     self._host, self._port, len(self._device_addresses), self._device_addresses)

        self._tx_task = self._hass.async_create_task(self._tx_loop())
        self._poll_task = self._hass.async_create_task(self._poll_loop())
        self._conn_task = self._hass.async_create_task(self._check_conn_loop())

    def stop(self) -> None:
        """Stop the gateway."""
        self._running = False
        _LOGGER.info("Stopping Merrytek gateway")

        for task in [self._tx_task, self._poll_task, self._conn_task]:
            if task:
                task.cancel()

        if self._transport:
            self._transport.close()
            self._transport = None
