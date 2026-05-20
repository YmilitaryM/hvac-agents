from pymodbus.client import AsyncModbusTcpClient
from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError

_REGISTER_COUNT = {"int16": 1, "int32": 2, "float32": 2}


class ModbusAdapter(ProtocolAdapter):
    protocol = "modbus"

    def __init__(self):
        self._client: AsyncModbusTcpClient | None = None

    async def connect(self, binding: ProtocolBinding) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        host = binding.config.get("host", "127.0.0.1")
        port = binding.config.get("port", 502)
        self._client = AsyncModbusTcpClient(host, port, timeout=5)
        connected = await self._client.connect()
        if not connected:
            raise CommunicationError(f"Modbus connect failed: {host}:{port}")

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        if self._client is None:
            raise CommunicationError("Not connected")
        slave_id = binding.config.get("slave_id", 1)
        register = binding.config.get("register", 40001)
        function_code = binding.config.get("function_code", 3)
        data_type = binding.config.get("data_type", "int16")
        scale = binding.config.get("scale", 1.0)
        offset = binding.config.get("offset", 0.0)
        reg_count = _REGISTER_COUNT.get(data_type, 1)

        try:
            if function_code == 3:
                rr = await self._client.read_holding_registers(register - 40001, reg_count, slave=slave_id)
            elif function_code == 4:
                rr = await self._client.read_input_registers(register - 30001, reg_count, slave=slave_id)
            else:
                raise CommunicationError(f"Unsupported function code: {function_code}")

            if rr.isError():
                raise CommunicationError(f"Modbus read error: {rr}")

            raw = rr.registers[0]
            if data_type == "int16" and raw > 32767:
                raw -= 65536
            value = raw * scale + offset
            return float(value)
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Modbus read failed: {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        if self._client is None:
            raise CommunicationError("Not connected")
        register = binding.config.get("register", 40001)
        if register < 40001:
            raise WriteError("Write only supported for holding registers (40001+)")
        slave_id = binding.config.get("slave_id", 1)
        scale = binding.config.get("scale", 1.0)
        offset = binding.config.get("offset", 0.0)
        raw_value = int((value - offset) / scale)
        try:
            result = await self._client.write_register(register - 40001, raw_value, slave=slave_id)
            if result.isError():
                raise WriteError(f"Modbus write error: {result}")
        except WriteError:
            raise
        except Exception as e:
            raise WriteError(f"Modbus write failed: {e}") from e

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
