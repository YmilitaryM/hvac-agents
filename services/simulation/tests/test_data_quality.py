from sim_service.data_quality.realtime_rules import RealtimeRules
from sim_service.data_quality.statistical import StatisticalDetector


def test_realtime_out_of_bounds():
    rules = RealtimeRules()
    rules.set_bounds("p1", -10.0, 50.0)
    event = rules.check_bounds("p1", "e1", 60.0)
    assert event is not None
    assert event.event_type == "out_of_bounds"
    assert event.severity == "critical"


def test_realtime_in_bounds():
    rules = RealtimeRules()
    rules.set_bounds("p1", -10.0, 50.0)
    event = rules.check_bounds("p1", "e1", 25.0)
    assert event is None


def test_realtime_no_bounds_configured():
    rules = RealtimeRules()
    event = rules.check_bounds("p1", "e1", 60.0)
    assert event is None


def test_statistical_frozen_sensor():
    detector = StatisticalDetector(freeze_window=5, freeze_threshold=0.001)
    for _ in range(5):
        event = detector.check_frozen("p1", "e1", 42.0)
    assert event is not None
    assert event.event_type == "sensor_frozen"


def test_statistical_spike():
    detector = StatisticalDetector()
    event = detector.check_spike("p1", "e1", current=500.0, previous=100.0, sigma=3.0)
    assert event is not None
    assert event.event_type == "spike"


def test_statistical_no_spike():
    detector = StatisticalDetector()
    event = detector.check_spike("p1", "e1", current=105.0, previous=100.0, sigma=3.0)
    assert event is None
