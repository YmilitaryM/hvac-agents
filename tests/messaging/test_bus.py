import pytest
from src.messaging.bus import (
    EventBus, Event, EventType, get_event_bus, reset_event_bus,
)


class TestEvent:
    def test_create_event(self):
        event = Event(
            event_type=EventType.STRATEGY_CREATED,
            source="strategy_agent",
            payload={"strategy_id": "s1"},
        )
        assert event.event_type == EventType.STRATEGY_CREATED
        assert event.source == "strategy_agent"
        assert event.payload["strategy_id"] == "s1"

    def test_event_auto_id(self):
        event = Event(event_type=EventType.CUSTOM, source="test")
        assert event.event_id != ""

    def test_event_to_dict(self):
        event = Event(event_type=EventType.FAULT_DETECTED, source="monitor", payload={"msg": "test"})
        d = event.to_dict()
        assert d["event_type"] == "fault_detected"
        assert d["source"] == "monitor"

    def test_event_from_dict(self):
        data = {
            "event_type": "anomaly_detected",
            "source": "monitor",
            "payload": {"level": "warning"},
            "timestamp": 1000.0,
        }
        event = Event.from_dict(data)
        assert event.event_type == EventType.ANOMALY_DETECTED
        assert event.source == "monitor"

    def test_event_json(self):
        event = Event(event_type=EventType.SYSTEM_STARTUP, source="main")
        json_str = event.to_json()
        assert "system_startup" in json_str


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_subscribe_and_publish(self, bus):
        received = []
        bus.subscribe(EventType.STRATEGY_APPROVED, lambda e: received.append(e))
        event = Event(EventType.STRATEGY_APPROVED, "coordinator", {"id": "s1"})
        bus.publish(event)
        assert len(received) == 1
        assert received[0].payload["id"] == "s1"

    def test_subscribe_all_receives_everything(self, bus):
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        bus.publish(Event(EventType.STRATEGY_CREATED, "strategy"))
        bus.publish(Event(EventType.FAULT_DETECTED, "monitor"))
        assert len(received) == 2

    def test_type_specific_handler_only_receives_own_type(self, bus):
        strategy_events = []
        fault_events = []
        bus.subscribe(EventType.STRATEGY_CREATED, lambda e: strategy_events.append(e))
        bus.subscribe(EventType.FAULT_DETECTED, lambda e: fault_events.append(e))
        bus.publish(Event(EventType.STRATEGY_CREATED, "strategy"))
        assert len(strategy_events) == 1
        assert len(fault_events) == 0

    def test_unsubscribe(self, bus):
        received = []
        def handler(e): received.append(e)
        token = bus.subscribe(EventType.CUSTOM, handler)
        bus.publish(Event(EventType.CUSTOM, "test"))
        assert len(received) == 1
        bus.unsubscribe(token)
        bus.publish(Event(EventType.CUSTOM, "test"))
        assert len(received) == 1  # unchanged

    def test_event_logging(self, bus):
        bus.publish(Event(EventType.CUSTOM, "a"))
        bus.publish(Event(EventType.CUSTOM, "b"))
        bus.publish(Event(EventType.CUSTOM, "c"))
        log = bus.get_event_log(2)
        assert len(log) == 2
        assert log[-1].source == "c"

    def test_get_events_by_type(self, bus):
        bus.publish(Event(EventType.STRATEGY_CREATED, "s"))
        bus.publish(Event(EventType.FAULT_DETECTED, "m"))
        bus.publish(Event(EventType.STRATEGY_APPROVED, "c"))
        created = bus.get_events_by_type(EventType.STRATEGY_CREATED)
        assert len(created) == 1

    def test_handler_exception_does_not_crash_bus(self, bus):
        def bad_handler(e): raise RuntimeError("oops")
        received = []
        bus.subscribe(EventType.CUSTOM, bad_handler)
        bus.subscribe(EventType.CUSTOM, lambda e: received.append(e))
        bus.publish(Event(EventType.CUSTOM, "test"))
        assert len(received) == 1  # second handler still called

    def test_clear_log(self, bus):
        bus.publish(Event(EventType.CUSTOM, "test"))
        assert len(bus.get_event_log()) == 1
        bus.clear_log()
        assert len(bus.get_event_log()) == 0

    def test_handler_count(self, bus):
        assert bus.handler_count == 0
        bus.subscribe(EventType.CUSTOM, lambda e: None)
        assert bus.handler_count == 1
        bus.subscribe_all(lambda e: None)
        assert bus.handler_count == 2


class TestGlobalBus:
    def teardown_method(self):
        reset_event_bus()

    def test_singleton(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset(self):
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2
