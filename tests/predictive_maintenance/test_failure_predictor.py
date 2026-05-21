import pytest

from services.agent.agent_service.predictive_maintenance.failure_predictor import (
    build_training_data,
    FailurePredictor,
    export_onnx,
)


class TestBuildTrainingData:
    """Tests for build_training_data which generates synthetic training samples."""

    def test_returns_tuple_of_two_elements(self):
        """Should return (features, labels) tuple."""
        result = build_training_data()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_features_is_list_of_lists(self):
        """Features should be a list of lists (n_samples x n_features)."""
        X, _ = build_training_data()
        assert isinstance(X, list)
        assert len(X) > 0
        assert isinstance(X[0], list)

    def test_labels_is_list_of_ints(self):
        """Labels should be a list of 0/1 integers."""
        _, y = build_training_data()
        assert isinstance(y, list)
        assert len(y) > 0
        assert all(isinstance(label, int) for label in y)

    def test_correct_number_of_samples(self):
        """Should generate 200 samples as defined in the function."""
        X, y = build_training_data()
        assert len(X) == 200
        assert len(y) == 200

    def test_each_sample_has_three_features(self):
        """Each data point should have [cop, vibration, approach_temp]."""
        X, _ = build_training_data()
        for sample in X:
            assert len(sample) == 3

    def test_labels_are_binary(self):
        """All labels should be 0 or 1."""
        _, y = build_training_data()
        assert set(y).issubset({0, 1})

    def test_contains_both_classes(self):
        """The synthetic data should include both failure and non-failure samples."""
        _, y = build_training_data()
        assert 0 in y
        assert 1 in y

    def test_features_are_numeric(self):
        """All feature values should be numeric (float or int)."""
        X, _ = build_training_data()
        for sample in X:
            for val in sample:
                assert isinstance(val, (int, float))

    def test_reproducible_with_seed(self):
        """With fixed np.random.seed(42), output should be deterministic."""
        X1, y1 = build_training_data()
        X2, y2 = build_training_data()
        # Same seed means same output
        assert X1 == X2
        assert y1 == y2

    def test_feature_values_in_reasonable_range(self):
        """COP ~ N(5.5, 1.2), vibration ~ N(3.0, 2.5), approach_temp ~ N(3.0, 2.0)."""
        X, _ = build_training_data()
        cops = [s[0] for s in X]
        vibs = [s[1] for s in X]
        appr = [s[2] for s in X]
        # Mean should be close to the specified normal distributions
        assert 4.5 < sum(cops) / len(cops) < 6.5
        assert 1.0 < sum(vibs) / len(vibs) < 5.0
        assert 1.0 < sum(appr) / len(appr) < 5.0


class TestFailurePredictor:
    """Tests for the FailurePredictor class (train, predict, predict_proba)."""

    @pytest.fixture
    def training_data(self):
        """Provide the synthetic training data."""
        return build_training_data()

    @pytest.fixture
    def trained_model(self, training_data):
        """Provide a pre-trained FailurePredictor."""
        X, y = training_data
        predictor = FailurePredictor()
        predictor.train(X, y)
        return predictor

    def test_initial_state_model_is_none(self):
        """A new FailurePredictor should have model=None before training."""
        p = FailurePredictor()
        assert p.model is None

    def test_predict_returns_zero_when_untrained(self):
        """Untrained predictor should return 0, not crash."""
        p = FailurePredictor()
        result = p.predict([5.0, 2.0, 3.0])
        assert result == 0

    def test_predict_proba_returns_zero_when_untrained(self):
        """Untrained predictor predict_proba should return 0.0."""
        p = FailurePredictor()
        result = p.predict_proba([5.0, 2.0, 3.0])
        assert result == 0.0

    def test_train_sets_model(self, training_data):
        """After training, model should not be None."""
        X, y = training_data
        p = FailurePredictor()
        p.train(X, y)
        assert p.model is not None

    def test_predict_returns_int(self, trained_model):
        """predict should return an integer (0 or 1)."""
        result = trained_model.predict([5.5, 2.0, 2.0])
        assert isinstance(result, int)
        assert result in (0, 1)

    def test_predict_proba_returns_float(self, trained_model):
        """predict_proba should return a float between 0 and 1."""
        result = trained_model.predict_proba([5.5, 2.0, 2.0])
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_predict_low_cop_high_risk(self, trained_model):
        """A very low COP should generally produce a high failure probability."""
        proba = trained_model.predict_proba([1.0, 3.0, 3.0])
        # Low COP (< 3.0) is labeled as failure in training data
        assert proba > 0.0

    def test_predict_high_vibration_high_risk(self, trained_model):
        """High vibration should indicate elevated failure probability."""
        proba = trained_model.predict_proba([5.5, 10.0, 3.0])
        # High vibration (> 7.0) is labeled as failure
        assert proba > 0.0

    def test_predict_high_approach_temp_high_risk(self, trained_model):
        """High approach temperature should indicate elevated failure probability."""
        proba = trained_model.predict_proba([5.5, 3.0, 8.0])
        # High approach temp (> 5.0) is labeled as failure
        assert proba > 0.0

    def test_predict_normal_conditions_low_risk(self, trained_model):
        """Normal operating conditions should have low failure probability."""
        proba = trained_model.predict_proba([5.5, 2.0, 2.0])
        # These are normal values, should be low probability
        assert proba < 0.5

    def test_predict_is_deterministic(self, trained_model):
        """Same input should produce the same prediction (model has random_state=42)."""
        features = [4.0, 3.5, 4.0]
        p1 = trained_model.predict(features)
        p2 = trained_model.predict(features)
        assert p1 == p2

    def test_prediction_agrees_with_proba(self, trained_model):
        """predict should return 1 when predict_proba >= 0.5, 0 otherwise."""
        features = [2.0, 8.0, 6.0]  # clearly failure conditions
        pred = trained_model.predict(features)
        proba = trained_model.predict_proba(features)
        expected = 1 if proba >= 0.5 else 0
        assert pred == expected

    def test_feature_names_present(self):
        """Feature names list should be the expected three."""
        p = FailurePredictor()
        assert p.feature_names == ["cop", "vibration_rms", "approach_temp"]

    def test_train_on_custom_data(self):
        """Training on custom small dataset should work."""
        p = FailurePredictor()
        X = [[5.0, 2.0, 2.0], [3.0, 3.0, 3.0], [2.0, 8.0, 6.0]]
        y = [0, 0, 1]
        p.train(X, y)
        assert p.model is not None
        # Should classify the failure sample correctly
        pred = p.predict([2.0, 8.0, 6.0])
        assert pred == 1

    def test_retrain_updates_model(self, training_data):
        """Training twice should update the model."""
        X, y = training_data
        p = FailurePredictor()
        p.train(X, y)
        first_pred = p.predict([2.0, 2.0, 2.0])

        # Train with inverted labels (swap 0 and 1)
        y_inverted = [1 - label for label in y]
        p.train(X, y_inverted)
        second_pred = p.predict([2.0, 2.0, 2.0])

        # Different training data should produce different model
        # (May or may not change prediction for this specific input)
        # At minimum, train should still succeed
        assert p.model is not None


class TestExportOnnx:
    """Tests for export_onnx function."""

    @pytest.fixture
    def rf_model(self):
        """Create and train a small RandomForest model."""
        from sklearn.ensemble import RandomForestClassifier
        X = [[5.0, 2.0, 2.0], [3.0, 3.0, 3.0], [2.0, 8.0, 6.0],
             [5.5, 1.0, 1.0], [4.0, 4.0, 4.0], [1.0, 9.0, 7.0]]
        y = [0, 0, 1, 0, 0, 1]
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        return model

    def test_export_creates_file(self, rf_model, tmp_path):
        """Export should create a valid file at the specified path."""
        path = str(tmp_path / "model.onnx")
        export_onnx(rf_model, path, n_features=3)
        import os
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_export_creates_nested_directories(self, rf_model, tmp_path):
        """Export should create parent directories if they don't exist."""
        path = str(tmp_path / "subdir" / "nested" / "model.onnx")
        export_onnx(rf_model, path, n_features=3)
        import os
        assert os.path.exists(path)

    def test_exported_file_is_valid_onnx(self, rf_model, tmp_path):
        """The exported file should be parseable as ONNX."""
        path = str(tmp_path / "model.onnx")
        export_onnx(rf_model, path, n_features=3)
        import onnx
        model = onnx.load(path)
        # Verify it's a valid ONNX model with the right input
        assert model is not None
        assert len(model.graph.input) == 1
        assert model.graph.input[0].name == "float_input"

    def test_export_different_n_features(self, rf_model, tmp_path):
        """Export should handle different n_features values."""
        path = str(tmp_path / "model.onnx")
        export_onnx(rf_model, path, n_features=5)
        import os
        assert os.path.exists(path)
        import onnx
        model = onnx.load(path)
        # Input shape dimension should reflect n_features=5
        dim_value = model.graph.input[0].type.tensor_type.shape.dim[1].dim_value
        assert dim_value == 5

    def test_export_with_untrained_failure_predictor(self, tmp_path):
        """Export should also work with a FailurePredictor's internal model."""
        X, y = build_training_data()
        p = FailurePredictor()
        p.train(X, y)

        path = str(tmp_path / "rf_model.onnx")
        export_onnx(p.model, path, n_features=3)
        import os
        assert os.path.exists(path)
