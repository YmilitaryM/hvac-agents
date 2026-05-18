"""Tests for RL contextual bandit and feature extraction."""

import numpy as np
import pytest

from src.rl.bandit import ContextualBandit, BanditPrediction, TrainingExample
from src.rl.features import extract_features, FEATURE_DIM, FEATURE_NAMES


class TestFeatureExtraction:
    """Tests for the feature extractor."""

    def test_extract_features_shape(self):
        """Feature vector should have shape (FEATURE_DIM,)."""
        features = extract_features(
            current_load_rt=750.0,
            predicted_load_rt=800.0,
            outdoor_wb_temp=28.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
        )
        assert features.shape == (FEATURE_DIM,)
        assert len(features) == FEATURE_DIM

    def test_extract_features_ranges(self):
        """All features should be in reasonable ranges."""
        features = extract_features(
            strategy={
                "actions": [{"action": "start", "device": "chiller_1"}],
                "expected_cop_improvement": 0.05,
                "expected_energy_saving_kwh_per_h": 100.0,
                "expected_carbon_saving_kg_per_h": 50.0,
                "transition_plan": {"total_duration_sec": 60, "phases": []},
            },
            current_load_rt=750.0,
            predicted_load_rt=800.0,
            outdoor_wb_temp=28.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
        )

        # Features 0-8 should be in [0, 1]
        for i in range(9):
            assert 0.0 <= features[i] <= 1.0, (
                f"Feature {i} ({FEATURE_NAMES[i]}): {features[i]} not in [0, 1]"
            )

        # cop_improvement feature (index 9) should be in [-0.2, 0.2]
        assert -0.2 <= features[9] <= 0.2, (
            f"COP improvement {features[9]} not in [-0.2, 0.2]"
        )

        # energy_saving (index 10) and carbon_saving (index 11) in [-1, 1]
        for i in (10, 11):
            assert -1.0 <= features[i] <= 1.0, (
                f"Feature {i} ({FEATURE_NAMES[i]}): {features[i]} not in [-1, 1]"
            )

    def test_extract_features_empty_strategy(self):
        """Should work with None and empty dict strategy."""
        features_none = extract_features(strategy=None)
        assert features_none.shape == (FEATURE_DIM,)

        features_empty = extract_features(strategy={})
        assert features_empty.shape == (FEATURE_DIM,)

        # With empty strategy, action count features should be 0
        assert features_empty[5] == 0.0  # num_actions
        assert features_empty[6] == 0.0  # num_start_actions
        assert features_empty[7] == 0.0  # num_stop_actions

    def test_extract_features_edge_cases(self):
        """Test feature extraction at edge values."""
        # Max load
        f = extract_features(current_load_rt=2000.0)
        assert f[0] == 1.0  # load_ratio capped at 1.0

        # Zero load
        f = extract_features(current_load_rt=0.0)
        assert f[0] == 0.0

        # Extreme outdoor temp
        f = extract_features(outdoor_wb_temp=50.0)
        assert f[2] == 1.0  # capped at 1.0

        # Zero price
        f = extract_features(electricity_price=0.0)
        assert f[3] == 0.0

        # High electricity price
        f = extract_features(electricity_price=5.0)
        assert f[3] == 1.0  # capped at 1.0

    def test_extract_features_many_actions(self):
        """Feature values for num_actions, num_starts, num_stops should be capped."""
        actions = [
            {"action": "start", "device": f"chiller_{i}"}
            for i in range(10)
        ]
        f = extract_features(strategy={"actions": actions})
        assert f[5] == 1.0  # 10 actions / 10 = 1.0
        assert f[6] == 1.0  # 10 starts / 5 = 2.0, capped at 1.0
        assert f[7] == 0.0  # no stops


class TestContextualBandit:
    """Tests for the ContextualBandit class."""

    @pytest.fixture
    def bandit(self):
        return ContextualBandit(epsilon=0.0, learning_rate=0.01)

    @pytest.fixture
    def sample_features(self):
        return extract_features(
            current_load_rt=750.0,
            predicted_load_rt=800.0,
            outdoor_wb_temp=28.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
        )

    def test_bandit_predict_returns_valid_action(self, bandit, sample_features):
        """Bandit prediction should return 'approve' or 'reject'."""
        with np.testing.assert_no_warnings():
            pred = bandit.predict(sample_features)
        assert pred.action in ("approve", "reject")
        assert isinstance(pred, BanditPrediction)

    def test_bandit_confidence_range(self, bandit, sample_features):
        """Confidence should be in [0, 1]."""
        pred = bandit.predict(sample_features)
        assert 0.0 <= pred.confidence <= 1.0

    def test_bandit_update_changes_weights(self, bandit, sample_features):
        """Weights should change after an update call."""
        old_approve = bandit.weights["approve"].copy()
        old_reject = bandit.weights["reject"].copy()

        bandit.update(sample_features, "approve", reward=1.0)

        # "approve" weights should change
        assert not np.allclose(old_approve, bandit.weights["approve"])

        # "reject" weights should NOT change (only "approve" was updated)
        assert np.allclose(old_reject, bandit.weights["reject"])

    def test_bandit_train_batch_reduces_loss(self, bandit):
        """Training on consistent examples should reduce loss."""
        # Create examples that clearly favor "approve"
        rng = np.random.RandomState(123)
        examples = []
        for _ in range(20):
            features = rng.normal(0.5, 0.1, FEATURE_DIM).astype(np.float64)
            # Make positive features → approve gets high reward
            features = np.clip(features, 0.0, 1.0)
            reward = 0.8 * np.mean(features[:5]) + 0.2  # reward correlates with early features
            examples.append(TrainingExample(
                features=features,
                action_taken="approve",
                reward=reward,
            ))

        losses = bandit.train_batch(examples, epochs=50)
        # Loss should decrease
        assert losses[-1] < losses[0], f"Loss did not decrease: {losses[0]} → {losses[-1]}"

    def test_bandit_epsilon_exploration(self, sample_features):
        """With epsilon=1.0, the bandit should explore (random actions)."""
        bandit = ContextualBandit(epsilon=1.0)

        # Run many predictions and check both actions appear
        actions = [bandit.predict(sample_features).action for _ in range(100)]
        assert "approve" in actions
        assert "reject" in actions

    def test_bandit_serialize_weights(self, bandit):
        """get_weights() and load_weights() should roundtrip correctly."""
        # First train a bit so weights aren't just the init values
        rng = np.random.RandomState(42)
        features = rng.normal(0.5, 0.1, FEATURE_DIM).astype(np.float64)
        bandit.update(features, "approve", 1.0)

        saved = bandit.get_weights()
        assert "approve" in saved
        assert "reject" in saved
        assert len(saved["approve"]) == FEATURE_DIM
        assert len(saved["reject"]) == FEATURE_DIM

        # Create new bandit and load
        bandit2 = ContextualBandit()
        bandit2.load_weights(saved)

        np.testing.assert_array_almost_equal(
            bandit.weights["approve"], bandit2.weights["approve"]
        )
        np.testing.assert_array_almost_equal(
            bandit.weights["reject"], bandit2.weights["reject"]
        )

    def test_bandit_convergence(self):
        """On linearly separable data, bandit should learn correct scores."""
        bandit = ContextualBandit(epsilon=0.0, learning_rate=0.1)

        examples = []
        for _ in range(200):
            # Good strategy: feature[0]=1 → approve=+1, reject=-1
            f_good = np.full(FEATURE_DIM, 0.5, dtype=np.float64)
            f_good[0] = 1.0
            examples.append(TrainingExample(features=f_good, action_taken="approve", reward=1.0))
            examples.append(TrainingExample(features=f_good.copy(), action_taken="reject", reward=-1.0))

            # Bad strategy: feature[0]=0 → approve=-1, reject=+1
            f_bad = np.full(FEATURE_DIM, 0.5, dtype=np.float64)
            f_bad[0] = 0.0
            examples.append(TrainingExample(features=f_bad, action_taken="approve", reward=-1.0))
            examples.append(TrainingExample(features=f_bad.copy(), action_taken="reject", reward=1.0))

        bandit.train_batch(examples, epochs=200)

        # Good features → approve should have higher score than reject
        test_good = np.full(FEATURE_DIM, 0.5, dtype=np.float64)
        test_good[0] = 1.0
        pred_good = bandit.predict(test_good)
        assert pred_good.score_approve > pred_good.score_reject, (
            f"Good features: approve={pred_good.score_approve:.3f} should be > reject={pred_good.score_reject:.3f}"
        )

        # Bad features → reject should have higher score than approve
        test_bad = np.full(FEATURE_DIM, 0.5, dtype=np.float64)
        test_bad[0] = 0.0
        pred_bad = bandit.predict(test_bad)
        assert pred_bad.score_approve < pred_bad.score_reject, (
            f"Bad features: approve={pred_bad.score_approve:.3f} should be < reject={pred_bad.score_reject:.3f}"
        )

    def test_training_example_creation(self):
        """TrainingExample should store features, action, and reward correctly."""
        features = np.ones(FEATURE_DIM, dtype=np.float64)
        ex = TrainingExample(features=features, action_taken="approve", reward=0.5)

        assert ex.action_taken == "approve"
        assert ex.reward == 0.5
        np.testing.assert_array_equal(ex.features, features)

    def test_feature_names_count(self):
        """FEATURE_NAMES should have FEATURE_DIM entries."""
        assert len(FEATURE_NAMES) == FEATURE_DIM
