import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from acquisition_service.poller import PollingEngine, PollingPoint
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError


async def wait_for_cycles(engine, n=1, timeout=5):
    for _ in range(timeout * 20):
        if engine._cycle_count >= n:
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"Only {engine._cycle_count}/{n} cycles completed")


@pytest.fixture
def mock_session_factory():
    session = AsyncMock()
    factory = MagicMock(return_value=session)
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return factory, session


@pytest.fixture
def mock_redis():
    return MagicMock()


class FakeAdapter:
    protocol = "modbus"
    def __init__(self):
        self.connected = False
    async def connect(self, binding):
        self.connected = True
    async def read_point(self, point_id, binding):
        return 42.0
    async def disconnect(self):
        self.connected = False


@pytest.mark.asyncio
async def test_poller_registers_and_polls_point(mock_session_factory, mock_redis):
    factory, session = mock_session_factory
    engine = PollingEngine(factory, mock_redis)
    await engine.start()

    binding = ProtocolBinding(protocol="modbus", config={"host": "127.0.0.1"})
    point = PollingPoint(
        point_id="p1", equipment_id="e1", plant_id="pl1",
        point_code="CHWST", binding=binding, poll_interval_sec=1
    )
    engine.register_point(point, FakeAdapter())

    await wait_for_cycles(engine, n=1)

    assert mock_redis.set.called or mock_redis.publish.called

    await engine.stop()


@pytest.mark.asyncio
async def test_poller_retries_on_failure(mock_session_factory, mock_redis):
    factory, session = mock_session_factory
    engine = PollingEngine(factory, mock_redis, retry_count=3)
    await engine.start()

    fail_adapter = FakeAdapter()
    fail_adapter.read_point = AsyncMock(side_effect=CommunicationError("comm error"))
    binding = ProtocolBinding(protocol="modbus", config={})
    point = PollingPoint(
        point_id="p2", equipment_id="e2", plant_id="pl1",
        point_code="CWST", binding=binding, poll_interval_sec=1
    )
    engine.register_point(point, fail_adapter)
    await wait_for_cycles(engine, n=1)

    assert fail_adapter.read_point.call_count == 3
    assert mock_redis.publish.called

    await engine.stop()
