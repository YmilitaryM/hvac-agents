def test_health_scorer_computes_score():
    from agent_service.health.health_scorer import compute_health_score
    metrics = {"cop_degradation_pct": 8.0, "vibration_rms": 5.5, "approach_temp_drift_k": 3.0,
               "run_hours": 12000, "days_since_maintenance": 90}
    result = compute_health_score(metrics)
    assert 0 <= result["overall_score"] <= 100
    assert "component_scores" in result
    assert result["trend_direction"] in ("up", "down", "stable")


def test_rul_estimator_weibull():
    from agent_service.health.rul_estimator import estimate_rul
    health_history = [95, 93, 90, 88, 85, 82, 80, 78, 75]
    result = estimate_rul(health_history, model="weibull", failure_threshold=60)
    assert result["predicted_hours"] > 0
    assert result["ci_lo"] <= result["predicted_hours"] <= result["ci_hi"]


def test_fault_diagnoser_matches_symptoms():
    from agent_service.health.fault_diagnoser import diagnose
    fmea_db = [
        {"id": 1, "failure_mode": "轴承磨损", "symptoms": {"vibration_rms": 7.5, "temp_rise": 12}},
        {"id": 2, "failure_mode": "不对中", "symptoms": {"vibration_rms": 5.0, "harmonic_2x": True}},
        {"id": 3, "failure_mode": "不平衡", "symptoms": {"vibration_rms": 4.0, "harmonic_1x": True}},
    ]
    symptoms = {"vibration_rms": 7.2, "temp_rise": 15, "harmonic_1x": False}
    result = diagnose(symptoms, fmea_db)
    assert len(result) >= 1
    assert result[0]["failure_mode"] == "轴承磨损"


def test_fft_analyzer_labels_frequencies():
    from agent_service.health.fft_analyzer import analyze_spectrum
    fft_bins = {50.0: 4.5, 100.0: 2.1, 150.0: 0.8, 200.0: 0.3}
    result = analyze_spectrum(fft_bins, shaft_speed_hz=50.0)
    assert "peak_frequencies" in result
    assert "vibration_zone" in result
    assert result["vibration_zone"] in ("A", "B", "C", "D")


def test_closed_loop_validates_accuracy():
    from agent_service.health.closed_loop import validate_predictions
    predictions = [{"id": 1, "predicted_hours": 2000, "actual_hours": 1800}]
    result = validate_predictions(predictions)
    assert "accuracy" in result
    assert result["accuracy"] > 0.5
    assert "should_retrain" in result
