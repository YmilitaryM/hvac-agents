import asyncio
import logging
from datetime import datetime, timezone

import duckdb

logger = logging.getLogger(__name__)


class Collector:
    """Polls hardware points via protocol adapters and writes readings to DuckDB."""

    def __init__(self, db: duckdb.DuckDBPyConnection, point_configs: dict, adapters: dict):
        self.db = db
        self.point_configs = point_configs
        self.adapters = adapters
        self._running = False
        self._task: asyncio.Task | None = None

    async def poll_once(self):
        now = datetime.now(timezone.utc).isoformat()
        for point_id, cfg in self.point_configs.items():
            adapter = self.adapters.get(cfg["protocol"])
            if not adapter:
                continue
            try:
                value = await adapter.read_point(point_id, cfg.get("binding", {}))
                self.db.execute(
                    "INSERT INTO readings (time, point_id, value, quality) VALUES (?, ?, ?, 'good')",
                    [now, point_id, value],
                )
            except Exception as e:
                logger.error(f"Failed to read {point_id}: {e}")
                self.db.execute(
                    "INSERT INTO readings (time, point_id, value, quality) VALUES (?, ?, ?, 'bad')",
                    [now, point_id, 0.0],
                )

    async def start(self, interval_ms: int = 1000):
        self._running = True
        self._task = asyncio.create_task(self._run_loop(interval_ms))

    async def _run_loop(self, interval_ms: int):
        while self._running:
            await self.poll_once()
            await asyncio.sleep(interval_ms / 1000.0)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
