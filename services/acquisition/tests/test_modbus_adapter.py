import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.modbus_adapter import ModbusAdapter


@pytest.mark.asyncio
async def test_modbus_read_holding_register():
    adapter = ModbusAdapter()
    binding = ProtocolBinding(protocol="modbus", config={
        "host": "127.0.0.1", "port": 5020,
        "slave_id": 1, "register": 40001,
        "function_code": 3, "data_type": "int16",
        "scale": 0.1, "offset": 0
    })
    await adapter.connect(binding)
    value = await adapter.read_point("test_point_1", binding)
    assert isinstance(value, float)
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_modbus_connection_timeout_raises_communication_error():
    adapter = ModbusAdapter()
    binding = ProtocolBinding(protocol="modbus", config={
        "host": "192.0.2.1", "port": 5020,
        "slave_id": 1, "register": 40001,
        "function_code": 3
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
