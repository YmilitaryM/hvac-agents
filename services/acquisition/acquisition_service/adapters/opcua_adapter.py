import asyncio
from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError


class OpcUaAdapter(ProtocolAdapter):
    protocol = "opc_ua"

    def __init__(self):
        self._client: object | None = None

    async def connect(self, binding: ProtocolBinding) -> None:
        if self._client is not None:
            await self.disconnect()
        endpoint_url = binding.config.get("endpoint_url")
        try:
            import asyncua
            self._client = asyncua.Client(url=endpoint_url, timeout=5)
            await asyncio.wait_for(self._client.connect(), timeout=10)
        except ImportError:
            raise CommunicationError("asyncua library not installed")
        except asyncio.TimeoutError:
            raise CommunicationError(f"OPC UA connect timeout: {endpoint_url}")
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"OPC UA connect failed: {endpoint_url} — {e}") from e

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        if self._client is None:
            raise CommunicationError("Not connected")
        node_id = binding.config.get("node_id")
        try:
            var = self._client.get_node(node_id)
            value = await var.read_value()
            return float(value)
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"OPC UA read failed: node={node_id} — {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        if self._client is None:
            raise CommunicationError("Not connected")
        node_id = binding.config.get("node_id")
        try:
            var = self._client.get_node(node_id)
            await var.write_value(value)
        except CommunicationError:
            raise
        except Exception as e:
            raise WriteError(f"OPC UA write failed: node={node_id} — {e}") from e

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
