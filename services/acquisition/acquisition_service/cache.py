import json


class PointCache:
    def __init__(self, redis):
        self._redis = redis

    async def set_latest(self, point_id: str, value: float, quality: str = "good") -> None:
        if not self._redis:
            return
        await self._redis.set(f"point:{point_id}:latest", json.dumps({"value": value, "quality": quality}))

    async def get_latest(self, point_id: str) -> dict | None:
        if not self._redis:
            return None
        raw = await self._redis.get(f"point:{point_id}:latest")
        return json.loads(raw) if raw else None

    async def get_latest_batch(self, point_ids: list[str]) -> dict[str, dict | None]:
        if not self._redis or not point_ids:
            return {}
        keys = [f"point:{pid}:latest" for pid in point_ids]
        results = await self._redis.mget(keys)
        return {
            pid: (json.loads(r) if r else None)
            for pid, r in zip(point_ids, results)
        }
