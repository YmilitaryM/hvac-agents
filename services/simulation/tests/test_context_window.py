from sim_service.data_quality.context_window import (
    BaselineComparator,
    DriftTracker,
    OperationalChecker,
    PeerComparator,
)
from sim_service.data_quality.realtime_rules import QualityEvent
from sim_service.data_quality.root_cause_analyzer import RootCauseAnalyzer, RootCauseCategory


def test_baseline_comparator_deviation():
    bc = BaselineComparator()
    # Build baseline
    for _ in range(10):
        bc.update_baseline("p1", 10, "weekday", 42.0)
    bc.update_baseline("p1", 10, "weekday", 52.0)  # deviation
    event = bc.check("p1", "e1", 10, "weekday", 52.0)
    assert event is not None
    assert event.event_type == "baseline_deviation"


def test_drift_tracker_detection():
    dt = DriftTracker()
    for _ in range(20):
        dt.update("p1", 42.0)
    # Inject drift
    for _ in range(20):
        dt.update("p1", 48.0)
    event = dt.check("p1", "e1")
    assert event is not None
    assert event.event_type == "drift_detected"


def test_peer_comparator_deviation():
    pc = PeerComparator()
    pc.add_peer_group("chillers", {"c1", "c2", "c3"})
    pc.update_value("c1", 42.0)
    pc.update_value("c2", 41.5)
    pc.update_value("c3", 42.5)
    event = pc.check("c4", "e4", 100.0, "chillers")
    assert event is not None
    assert event.event_type == "peer_deviation"


def test_operational_freeze_risk():
    oc = OperationalChecker()
    event = oc.check_freeze_risk("p1", "e1", -1.0)
    assert event is not None
    assert event.event_type == "freeze_risk"


def test_operational_missing_free_cooling():
    oc = OperationalChecker()
    event = oc.check_missing_free_cooling("p1", "e1", ambient_temp=5.0, is_mechanical_cooling=True)
    assert event is not None
    assert event.event_type == "missing_free_cooling"


def test_root_cause_sensor_fault():
    analyzer = RootCauseAnalyzer()
    events = [
        QualityEvent("p1", "e1", "sensor_frozen", "high", 42.0, None),
    ]
    result = analyzer.analyze("p1", "e1", events)
    assert result.primary_cause == RootCauseCategory.SENSOR_FAULT
    assert result.confidence > 0.5


def test_root_cause_comm_failure():
    analyzer = RootCauseAnalyzer()
    events = [
        QualityEvent("p1", "e1", "communication_lost", "critical", None, None),
        QualityEvent("p1", "e1", "out_of_bounds", "critical", 999.0, 50.0),
    ]
    result = analyzer.analyze("p1", "e1", events)
    assert result.primary_cause == RootCauseCategory.COMM_FAILURE
