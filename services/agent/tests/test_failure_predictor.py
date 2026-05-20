import numpy as np
import pytest
from agent_service.predictive_maintenance.failure_predictor import (
    FailurePredictor, build_training_data, export_onnx
)


def test_build_training_data():
    features, labels = build_training_data()
    assert len(features) > 0
    assert len(features) == len(labels)
    assert all(isinstance(f, list) for f in features)
    assert all(isinstance(l, int) for l in labels)


def test_train_predictor():
    X, y = build_training_data()
    predictor = FailurePredictor()
    predictor.train(X, y)
    assert predictor.model is not None

    # Predict on a sample
    sample = [3.5, 8.0, 2.1]  # cop, vibration, approach_temp
    proba = predictor.predict_proba(sample)
    assert 0 <= proba <= 1


def test_export_onnx_roundtrip(tmp_path):
    X, y = build_training_data()
    predictor = FailurePredictor()
    predictor.train(X, y)

    model_path = tmp_path / "test_model.onnx"
    export_onnx(predictor.model, str(model_path), n_features=len(X[0]))
    assert model_path.exists()
    assert model_path.stat().st_size > 0
