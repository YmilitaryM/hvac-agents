import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker

from .adapters.base import ProtocolBinding, ProtocolAdapter, CommunicationError
from .models import EquipmentReading

logger = logging.getLogger(__name__)


@dataclass
class PollingPoint:
    point_id: str
    equipment_id: str
    plant_id: str
    point_code: str
    binding: ProtocolBinding
    poll_interval_sec: float = 10
    last_poll: float = 0
    last_value: float | None = None


class PollingEngine:
    def __init__(self, session_factory: async_sessionmaker, redis, retry_count: int = 3):
        self._session_factory = session_factory
        self._redis = redis
        self._retry_count = retry_count
        self._points: dict[str, tuple[PollingPoint, ProtocolAdapter]] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        self._cycle_count = 0

    def register_point(self, point: PollingPoint, adapter: ProtocolAdapter) -> None:
        self._points[point.point_id] = (point, adapter)

    def unregister_point(self, point_id: str) -> None:
        self._points.pop(point_id, None)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc).timestamp()
            batch = []

            for point_id, (pt, adapter) in list(self._points.items()):
                if now - pt.last_poll >= pt.poll_interval_sec:
                    batch.append((pt, adapter))

            if batch:
                results = await asyncio.gather(
                    *[self._poll_single(pt, adapter) for pt, adapter in batch],
                    return_exceptions=True
                )
                for (pt, _), result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"Polling failed for {pt.point_code}: {result}")
                    elif result is not None:
                        pt.last_value = result
                    pt.last_poll = now

            self._cycle_count += 1
            await asyncio.sleep(0.1)

    async def _poll_single(self, point: PollingPoint, adapter: ProtocolAdapter) -> float | None:
        for attempt in range(self._retry_count):
            try:
                value = await adapter.read_point(point.point_id, point.binding)
                point.last_value = value
                try:
                    await self._forward_value(point, value, "good")
                except Exception:
                    logger.warning(
                        f"Storage forward failed for {point.point_code}, value preserved",
                        exc_info=True,
                    )
                return value
            except CommunicationError as e:
                if attempt == self._retry_count - 1:
                    await self._forward_value(point, point.last_value, "bad")
                    await self._publish_event("point.communication_lost", {
                        "point_id": point.point_id,
                        "equipment_id": point.equipment_id,
                        "point_code": point.point_code,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def _forward_value(self, point: PollingPoint, value: float | None, quality: str) -> None:
        if value is None:
            return
        now = datetime.now(timezone.utc)
        reading = EquipmentReading(
            time=now, equipment_id=point.equipment_id,
            plant_id=point.plant_id, point_id=point.point_id,
            point_code=point.point_code, value=value,
            quality=quality, source="live"
        )
        async with self._session_factory() as session:
            session.add(reading)
            await session.commit()

        if self._redis:
            await self._redis.set(
                f"point:{point.point_id}:latest",
                json.dumps({"value": value, "quality": quality, "ts": now.isoformat()})
            )

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        if self._redis:
            await self._redis.publish(
                f"events:{event_type}",
                json.dumps(payload)
            )
