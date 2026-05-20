import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.opcua_adapter import OpcUaAdapter


@pytest.mark.asyncio
async def test_opcua_connection_failure():
    adapter = OpcUaAdapter()
    binding = ProtocolBinding(protocol="opc_ua", config={
        "endpoint_url": "opc.tcp://192.0.2.1:4840",
        "node_id": "ns=2;s=Temperature",
        "poll_interval_sec": 1
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
