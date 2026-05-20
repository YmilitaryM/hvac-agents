import json
from datetime import datetime, timezone

import duckdb


class SyncQueue:
    """DuckDB-backed persistent outbox for offline-tolerant MQTT publishing."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.db = db

    def enqueue(self, topic: str, payload: dict, qos: int = 1):
        now = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload)
        self.db.execute(
            "INSERT INTO sync_queue (id, created_at, topic, payload, qos, retries, synced) "
            "VALUES (nextval('seq_sync_queue_id'), ?, ?, ?, ?, 0, FALSE)",
            [now, topic, payload_str, qos],
        )

    def get_unsent(self, limit: int = 100) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, created_at, topic, payload, qos, retries "
            "FROM sync_queue WHERE synced = FALSE ORDER BY id ASC LIMIT ?",
            [limit],
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "topic": r[2], "payload": r[3], "qos": r[4], "retries": r[5]}
            for r in rows
        ]

    def mark_synced(self, ids: list[int]):
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        self.db.execute(
            f"UPDATE sync_queue SET synced = TRUE WHERE id IN ({placeholders})", ids
        )
