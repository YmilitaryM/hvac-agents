import asyncio
import json
import logging

import duckdb
import httpx

from .queue import SyncQueue

logger = logging.getLogger(__name__)


class SyncAgent:
    """Handles edge-to-cloud sync via MQTT (real-time) and HTTP (bulk)."""

    def __init__(self, db: duckdb.DuckDBPyConnection, config):
        self.db = db
        self.cfg = config
        self.queue = SyncQueue(db)
        self._http = httpx.AsyncClient(base_url=config.cloud_api_url, timeout=30.0)
        self._running = False
        self._task: asyncio.Task | None = None

    async def send_alert(self, severity: str, title: str, equipment_id: str = ""):
        payload = {
            "edge_id": self.cfg.edge_id,
            "severity": severity,
            "title": title,
            "equipment_id": equipment_id,
        }
        topic = f"hvac/{self.cfg.edge_id}/alert"
        self.queue.enqueue(topic, payload, qos=1)

    async def flush_mqtt(self, publish_fn):
        items = self.queue.get_unsent()
        synced = []
        for item in items:
            try:
                payload = json.loads(item["payload"])
                await publish_fn(item["topic"], payload, item["qos"])
                synced.append(item["id"])
            except Exception as e:
                logger.warning(f"Failed to publish {item['id']}: {e}")
                self.db.execute(
                    "UPDATE sync_queue SET retries = retries + 1 WHERE id = ?", [item["id"]]
                )
        self.queue.mark_synced(synced)

    async def upload_readings(self):
        last_sent = self.db.execute(
            "SELECT last_sent_at FROM sync_meta WHERE table_name = 'readings'"
        ).fetchone()
        since = last_sent[0] if last_sent else "1970-01-01T00:00:00Z"

        agg_rows = self.db.execute("""
            SELECT
                time_bucket(INTERVAL '15 minutes', time) AS bucket,
                point_id,
                MIN(value) AS v_min,
                MAX(value) AS v_max,
                AVG(value) AS v_avg,
                STDDEV(value) AS v_std
            FROM readings
            WHERE time > ?
            GROUP BY bucket, point_id
            ORDER BY bucket
        """, [since]).fetchall()

        if not agg_rows:
            return

        readings = [
            {"time": r[0].isoformat(), "point_id": r[1],
             "min": r[2], "max": r[3], "avg": r[4], "std": r[5]}
            for r in agg_rows
        ]

        try:
            resp = await self._http.post(
                f"/api/edges/{self.cfg.edge_id}/data/ingest",
                json={"readings": readings, "inspections": [], "work_orders": []},
            )
            if resp.status_code == 200:
                latest = max(r["time"] for r in readings)
                self.db.execute(
                    "INSERT OR REPLACE INTO sync_meta (table_name, last_sent_at) VALUES ('readings', ?)",
                    [latest],
                )
        except Exception as e:
            logger.error(f"Upload failed: {e}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())

    async def _sync_loop(self):
        while self._running:
            try:
                await self.upload_readings()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            await asyncio.sleep(30)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        await self._http.aclose()
