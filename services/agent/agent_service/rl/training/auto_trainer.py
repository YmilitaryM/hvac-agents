import asyncio
import logging

logger = logging.getLogger(__name__)


class AutoTrainer:
    """Periodic automatic DRL training scheduler."""

    def __init__(self, controller, session_factory, redis, train_interval_hours: int = 24):
        self._controller = controller
        self._session_factory = session_factory
        self._redis = redis
        self._interval = train_interval_hours * 3600
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await self._train_cycle()
            except Exception as e:
                logger.error(f"Auto-training failed: {e}")
            await asyncio.sleep(self._interval)

    async def _train_cycle(self):
        logger.info("Starting auto-training cycle")
        if self._redis:
            await self._redis.publish("events:rl.training_completed", "{}")
