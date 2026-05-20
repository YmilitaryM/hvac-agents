import numpy as np

from agent_service.anomaly.autoencoder import AutoencoderAnomalyDetector, HAS_TORCH
from agent_service.anomaly.feature_builder import FeatureBuilder
from agent_service.anomaly.isolation_forest import IsolationForestDetector


def test_feature_builder_equipment_vector():
    sensors = {"temp_chw_s": 6.5, "temp_chw_r": 12.3, "flow": 100.0}
    order = ["temp_chw_s", "temp_chw_r", "flow", "temp_cw_s"]
    vec = FeatureBuilder.build_equipment_vector(sensors, order)
    assert vec.tolist() == [6.5, 12.3, 100.0, 0.0]


def test_feature_builder_normalize():
    vectors = np.array([[1.0, 10.0], [3.0, 20.0]], dtype=np.float64)
    normed = FeatureBuilder.normalize_vectors(vectors)
    assert normed.shape == (2, 2)
    assert abs(normed.mean(axis=0)[0]) < 1e-10
    assert abs(normed.std(axis=0)[0] - 1.0) < 1e-10


def test_feature_builder_efficiency_vector():
    metrics = {"cop": 5.0, "kw_per_rt": 0.7, "approach_temp": 3.5, "plr": 0.8}
    vec = FeatureBuilder.build_efficiency_vector(metrics)
    assert len(vec) == 6
    assert vec[0] == 5.0
    assert vec[-1] == 0.0  # delta_t_cw not provided


def test_isolation_forest_fit_and_predict():
    rng = np.random.RandomState(42)
    normal_data = rng.randn(100, 6)
    outlier = np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])

    detector = IsolationForestDetector(contamination=0.05)
    detector.fit(normal_data)

    normal_result = detector.predict(normal_data[0])
    assert not normal_result["anomaly"]

    outlier_result = detector.predict(outlier)
    assert outlier_result["anomaly"]


def test_isolation_forest_not_fitted():
    detector = IsolationForestDetector()
    result = detector.predict(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
    assert not result["anomaly"]
    assert result["score"] == 0.0


def test_autoencoder_detector_no_torch():
    detector = AutoencoderAnomalyDetector(input_dim=6)
    result = detector.predict(np.array([1.0] * 6))
    if HAS_TORCH:
        assert "anomaly" in result
    else:
        assert not result["anomaly"]
        assert result["error"] == 0.0


def test_autoencoder_train_and_predict():
    if not HAS_TORCH:
        return

    rng = np.random.RandomState(42)
    normal_data = rng.randn(200, 4).astype(np.float32)
    anomaly = np.array([5.0, 5.0, 5.0, 5.0], dtype=np.float32)

    detector = AutoencoderAnomalyDetector(input_dim=4, learning_rate=0.01)
    detector.train(normal_data, epochs=30)

    normal_result = detector.predict(normal_data[0])
    assert not normal_result["anomaly"], f"expected non-anomalous, got {normal_result}"

    anomaly_result = detector.predict(anomaly)
    assert anomaly_result["anomaly"], f"expected anomalous, got {anomaly_result}"
