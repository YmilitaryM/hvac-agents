import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.bacnet_adapter import BacnetAdapter


@pytest.mark.asyncio
async def test_bacnet_read_analog_input():
    adapter = BacnetAdapter()
    binding = ProtocolBinding(protocol="bacnet", config={
        "device_id": 2401,
        "object_type": "analog_input",
        "instance": 12,
        "poll_interval_sec": 5
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
