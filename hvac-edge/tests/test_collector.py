import os, tempfile, asyncio
import pytest
from edge.db import init_db
from edge.engine.collector import Collector


class FakeAdapter:
    """Simulates a protocol adapter returning fixed values."""
    def __init__(self, points: dict[str, float]):
        self.points = points
        self.connected = False

    async def connect(self, binding: dict):
        self.connected = True

    async def read_point(self, point_id: str, binding: dict) -> float:
        return self.points.get(point_id, 0.0)

    async def disconnect(self):
        self.connected = False


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_collector.duckdb")
    return init_db(path)


@pytest.mark.asyncio
async def test_collector_poll_and_store(db):
    config = {
        "p1": {"protocol": "fake", "binding": {}, "poll_interval_ms": 100},
        "p2": {"protocol": "fake", "binding": {}, "poll_interval_ms": 100},
    }
    adapter = FakeAdapter({"p1": 23.5, "p2": 45.0})
    collector = Collector(db, config, {"fake": adapter})

    await collector.poll_once()

    rows = db.execute("SELECT point_id, value FROM readings ORDER BY point_id").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("p1", 23.5)
    assert rows[1] == ("p2", 45.0)
