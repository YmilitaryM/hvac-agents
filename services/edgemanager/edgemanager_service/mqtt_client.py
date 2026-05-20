import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class EdgeMQTTClient:
    """Cloud-side MQTT client for edge communication."""

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._connected = False
        self._handlers: dict[str, list] = {}

    def on_topic(self, topic: str, handler):
        self._handlers.setdefault(topic, []).append(handler)

    async def start(self):
        logger.info(f"MQTT client configured for {self.broker_host}:{self.broker_port}")
        self._connected = True

    async def stop(self):
        self._connected = False

    async def publish(self, topic: str, payload: dict, qos: int = 1):
        logger.info(f"MQTT publish → {topic}: {json.dumps(payload)}")
