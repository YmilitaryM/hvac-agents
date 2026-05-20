import asyncio
import logging

logger = logging.getLogger(__name__)


class EdgeSync:
    """Push local acq_db batches to cloud when connection is restored."""

    def __init__(self, session_factory, redis, cloud_url: str, batch_size: int = 500):
        self._session_factory = session_factory
        self._redis = redis
        self._cloud_url = cloud_url.rstrip("/")
        self._batch_size = batch_size
        self._last_synced_id = 0

    async def sync_pending(self) -> int:
        from .models import EquipmentReading
        synced = 0
        async with self._session_factory() as session:
            result = await session.execute(
                "SELECT * FROM equipment_readings WHERE id > :last_id ORDER BY id LIMIT :limit",
                {"last_id": self._last_synced_id, "limit": self._batch_size}
            )
            rows = result.fetchall()
            if rows:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    payload = [{
                        "time": r.time.isoformat(), "equipment_id": r.equipment_id,
                        "plant_id": r.plant_id, "point_id": r.point_id,
                        "point_code": r.point_code, "value": r.value,
                        "quality": r.quality, "source": r.source,
                    } for r in rows]
                    resp = await client.post(f"{self._cloud_url}/api/acquisition/sync", json={"readings": payload})
                    if resp.status_code == 200:
                        self._last_synced_id = rows[-1].id
                        synced = len(rows)
                        if self._redis:
                            await self._redis.set("edge:last_synced_id", str(self._last_synced_id))
        return synced

    async def run_sync_loop(self, interval_sec: int = 30):
        while True:
            try:
                count = await self.sync_pending()
                if count > 0:
                    logger.info(f"Edge sync: pushed {count} readings to cloud")
            except Exception as e:
                logger.error(f"Edge sync failed: {e}")
            await asyncio.sleep(interval_sec)
