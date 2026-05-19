"""In-process event bus for decoupled agent communication.

Provides publish/subscribe semantics. Redis backend is optional ---
defaults to in-process message passing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging
import time
import json

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types in the HVAC system."""
    # Monitoring events
    ANOMALY_DETECTED = "anomaly_detected"
    HEALTH_CHANGE = "health_change"

    # Strategy events
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_APPROVED = "strategy_approved"
    STRATEGY_REJECTED = "strategy_rejected"
    STRATEGY_EXECUTED = "strategy_executed"
    STRATEGY_ABORTED = "strategy_aborted"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    FAULT_DETECTED = "fault_detected"

    # Report events
    REPORT_GENERATED = "report_generated"

    # Generic
    CUSTOM = "custom"


@dataclass
class Event:
    """An event in the system."""
    event_type: EventType
    source: str  # component that emitted the event
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"{self.event_type.value}_{int(self.timestamp * 1000)}_{id(self) % 10000}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_type=EventType(data["event_type"]),
            source=data["source"],
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            event_id=data.get("event_id", ""),
        )


# Callback type: function that receives an Event and returns nothing
EventCallback = Callable[[Event], None]

# Subscription token: (event_type, callback_id) for safe unsubscription
SubscriptionToken = tuple


class EventBus:
    """In-process event bus with publish/subscribe semantics.

    Supports subscribing to specific event types or all events.
    Handlers are called synchronously when an event is published.

    Usage:
        bus = EventBus()
        token = bus.subscribe(EventType.STRATEGY_APPROVED, my_handler)
        bus.publish(Event(EventType.STRATEGY_APPROVED, "coordinator", {...}))
        bus.unsubscribe(token)
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[EventCallback]] = {}
        self._catch_all_handlers: List[EventCallback] = []
        self._event_log: List[Event] = []
        self._max_log_size: int = 1000

    def subscribe(self, event_type: EventType, callback: EventCallback) -> SubscriptionToken:
        """Subscribe to a specific event type. Returns a token for unsubscribe()."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(callback)
        return (event_type, id(callback))

    def subscribe_all(self, callback: EventCallback) -> SubscriptionToken:
        """Subscribe to all events. Returns a token for unsubscribe()."""
        self._catch_all_handlers.append(callback)
        return (None, id(callback))

    def unsubscribe(self, token: SubscriptionToken) -> None:
        """Unsubscribe using a token returned by subscribe() or subscribe_all()."""
        event_type, callback_id = token
        if event_type is None:
            self._catch_all_handlers = [
                h for h in self._catch_all_handlers if id(h) != callback_id
            ]
        elif event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if id(h) != callback_id
            ]

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Calls type-specific handlers first, then catch-all handlers.
        Failed handlers are caught and logged (don't crash the bus).
        """
        logger.debug("Publishing event: %s from %s", event.event_type.value, event.source)

        # Log the event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Call type-specific handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.warning(
                    "Handler %s failed for event %s",
                    getattr(handler, "__name__", handler),
                    event.event_type.value,
                    exc_info=True,
                )

        # Call catch-all handlers
        for handler in self._catch_all_handlers:
            try:
                handler(event)
            except Exception:
                logger.warning(
                    "Catch-all handler %s failed for event %s",
                    getattr(handler, "__name__", handler),
                    event.event_type.value,
                    exc_info=True,
                )

    def get_event_log(self, n: int = 100) -> List[Event]:
        """Get the most recent events."""
        return self._event_log[-n:]

    def get_events_by_type(self, event_type: EventType, n: int = 100) -> List[Event]:
        """Get recent events of a specific type."""
        matching = [e for e in self._event_log if e.event_type == event_type]
        return matching[-n:]

    def clear_log(self) -> None:
        """Clear the event log."""
        self._event_log = []

    def clear_handlers(self) -> None:
        """Remove all handlers."""
        self._handlers = {}
        self._catch_all_handlers = []

    @property
    def handler_count(self) -> int:
        """Total number of registered handlers."""
        type_handlers = sum(len(h) for h in self._handlers.values())
        return type_handlers + len(self._catch_all_handlers)


# Global singleton
_default_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the default event bus singleton."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_event_bus() -> None:
    """Reset the default event bus (useful for testing)."""
    global _default_bus
    _default_bus = None
