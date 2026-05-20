import os, tempfile, json
import pytest
from edge.db import init_db
from edge.sync.queue import SyncQueue


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_sync.duckdb")
    return init_db(path)


class TestSyncQueue:
    def test_enqueue_and_dequeue(self, db):
        q = SyncQueue(db)
        q.enqueue("hvac/edge-1/alert", {"severity": "critical"}, qos=1)

        items = q.get_unsent()
        assert len(items) == 1
        assert items[0]["topic"] == "hvac/edge-1/alert"
        assert json.loads(items[0]["payload"]) == {"severity": "critical"}

    def test_mark_synced(self, db):
        q = SyncQueue(db)
        q.enqueue("hvac/edge-1/status", {"ok": True}, qos=1)
        items = q.get_unsent()
        q.mark_synced([items[0]["id"]])

        remaining = q.get_unsent()
        assert len(remaining) == 0

    def test_fifo_order(self, db):
        q = SyncQueue(db)
        q.enqueue("a/b/c", {"n": 1}, qos=1)
        q.enqueue("a/b/c", {"n": 2}, qos=1)
        q.enqueue("a/b/c", {"n": 3}, qos=1)

        items = q.get_unsent()
        payloads = [json.loads(i["payload"])["n"] for i in items]
        assert payloads == [1, 2, 3]

    def test_retry_count(self, db):
        q = SyncQueue(db)
        q.enqueue("a/b/c", {"x": 1}, qos=1)
        items = q.get_unsent()
        assert items[0]["retries"] == 0
