"""WebSocket endpoint for real-time monitoring."""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.messaging.bus import Event, get_event_bus, EventType

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._subscriptions: dict[str, set] = {}  # conn_id -> set of EventType values

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = f"ws_{int(time.time() * 1000)}_{id(websocket) % 10000}"
        self._connections[conn_id] = websocket
        self._subscriptions[conn_id] = set()  # empty = all events
        logger.info("WebSocket connected: %s (total=%d)", conn_id, len(self._connections))
        return conn_id

    def disconnect(self, conn_id: str) -> None:
        self._connections.pop(conn_id, None)
        self._subscriptions.pop(conn_id, None)
        logger.info("WebSocket disconnected: %s (total=%d)", conn_id, len(self._connections))

    def update_subscriptions(self, conn_id: str, event_types: set) -> None:
        self._subscriptions[conn_id] = event_types

    async def broadcast(self, event: Event) -> None:
        data = event.to_dict()
        try:
            payload = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning("Cannot serialize event %s: %s", event.event_type.value, e)
            return
        dead: list[str] = []
        for conn_id, ws in self._connections.items():
            subs = self._subscriptions.get(conn_id, set())
            if subs and event.event_type.value not in subs:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(conn_id)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()


def on_event(event: Event) -> None:
    """Sync callback for the event bus — schedules broadcast on the event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(event))
    except RuntimeError:
        logger.debug("Event loop not running, dropping event %s", event.event_type.value)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    conn_id = await manager.connect(websocket)
    bus = get_event_bus()
    token = bus.subscribe_all(on_event)

    heartbeat_task = asyncio.create_task(_send_heartbeat(websocket, conn_id))

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if "ping" in data:
                await websocket.send_text(json.dumps({"pong": time.time()}))
            elif "subscribe" in data:
                types = set(data["subscribe"])
                manager.update_subscriptions(conn_id, types)
                await websocket.send_text(json.dumps({"subscribed": list(types)}))
            elif "unsubscribe" in data:
                manager.update_subscriptions(conn_id, set())
                await websocket.send_text(json.dumps({"unsubscribed": True}))

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected: %s", conn_id)
    except Exception:
        logger.warning("WebSocket error for %s", conn_id, exc_info=True)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        bus.unsubscribe(token)
        manager.disconnect(conn_id)


async def _send_heartbeat(ws: WebSocket, conn_id: str) -> None:
    try:
        while True:
            await asyncio.sleep(15)
            try:
                await ws.send_text(json.dumps({"heartbeat": time.time()}))
            except Exception:
                logger.debug("Heartbeat failed for %s", conn_id)
                break
    except asyncio.CancelledError:
        pass
