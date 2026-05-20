import asyncio
import socket

import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.modbus_adapter import ModbusAdapter

MODBUS_HOST = "127.0.0.1"
MODBUS_PORT = 5020


def _modbus_server_available() -> bool:
    """Check if a Modbus TCP server is listening on the test port."""
    try:
        s = socket.create_connection((MODBUS_HOST, MODBUS_PORT), timeout=0.5)
        s.close()
        return True
    except OSError:
        return False


@pytest.mark.asyncio
async def test_modbus_read_holding_register():
    """Requires a running Modbus TCP server on 127.0.0.1:5020."""
    if not _modbus_server_available():
        pytest.skip(f"No Modbus server on {MODBUS_HOST}:{MODBUS_PORT}")

    adapter = ModbusAdapter()
    binding = ProtocolBinding(protocol="modbus", config={
        "host": MODBUS_HOST, "port": MODBUS_PORT,
        "slave_id": 1, "register": 40001,
        "function_code": 3, "data_type": "int16",
        "scale": 0.1, "offset": 0,
    })
    await adapter.connect(binding)
    try:
        value = await adapter.read_point("test_point_1", binding)
        assert isinstance(value, float)
    finally:
        await adapter.disconnect()


@pytest.mark.asyncio
async def test_modbus_connect_to_dead_host_errors_on_read():
    """Connect to a reachable host with no Modbus server — read must fail."""
    adapter = ModbusAdapter()
    # localhost with a port where nothing listening — connect returns False,
    # adapter raises CommunicationError immediately during connect.
    binding = ProtocolBinding(protocol="modbus", config={
        "host": "127.0.0.1", "port": 5020,
        "slave_id": 1, "register": 40001,
        "function_code": 3,
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
