"""Tests for the offline trainer that builds bandit training examples from memory."""

import numpy as np
import pytest

from src.rl.bandit import ContextualBandit, TrainingExample
from src.rl.trainer import (
    build_training_examples,
    train_from_memory,
    compute_reward_from_strategy,
)
from src.rl.features import FEATURE_DIM


class TestBuildTrainingExamples:
    """Tests for building training examples from memory entries."""

    def test_build_training_examples_empty(self):
        """Empty list should produce empty examples."""
        examples = build_training_examples([])
        assert examples == []
        assert len(examples) == 0

    def test_build_training_examples_success(self):
        """Completed + safety passed + COP improvement → reward=1.0."""
        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                "electricity_price": 0.8,
                "carbon_intensity": 0.5,
                "execution_status": "completed",
                "safety_passed": True,
                "cop_improvement": 0.05,
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == 1.0
        assert examples[0].action_taken == "approve"
        assert examples[0].features.shape == (FEATURE_DIM,)

    def test_build_training_examples_neutral(self):
        """Completed + safety passed + neutral COP → reward=0.5."""
        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                "execution_status": "completed",
                "safety_passed": True,
                "cop_improvement": 0.0,
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == 0.5

    def test_build_training_examples_safety_failed(self):
        """Completed but safety failed → reward=-0.5."""
        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                "execution_status": "completed",
                "safety_passed": False,
                "cop_improvement": 0.03,
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == -0.5

    def test_build_training_examples_aborted(self):
        """Aborted → reward=-1.0."""
        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                "execution_status": "aborted",
                "safety_passed": True,
                "cop_improvement": 0.0,
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == -1.0

    def test_build_training_examples_negative_cop(self):
        """Completed + safety passed + negative COP → reward=-0.5."""
        entries = [
            {
                "current_load_rt": 600.0,
                "predicted_load_rt": 600.0,
                "execution_status": "completed",
                "safety_passed": True,
                "cop_improvement": -0.10,
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == -0.5

    def test_build_training_examples_default_values(self):
        """Missing optional fields should use defaults."""
        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                # No electricity_price, carbon_intensity
            }
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 1
        assert examples[0].reward == -1.0  # default status is not in entry → aborted
        assert examples[0].features.shape == (FEATURE_DIM,)

    def test_build_training_examples_multiple(self):
        """Multiple entries with different reward levels."""
        entries = [
            {"current_load_rt": 750, "predicted_load_rt": 800,
             "execution_status": "completed", "safety_passed": True, "cop_improvement": 0.05},
            {"current_load_rt": 500, "predicted_load_rt": 600,
             "execution_status": "aborted", "safety_passed": False, "cop_improvement": 0.0},
            {"current_load_rt": 900, "predicted_load_rt": 850,
             "execution_status": "completed", "safety_passed": True, "cop_improvement": -0.05},
        ]
        examples = build_training_examples(entries)
        assert len(examples) == 3
        assert examples[0].reward == 1.0  # success
        assert examples[1].reward == -1.0  # aborted
        assert examples[2].reward == -0.5  # negative cop


class TestTrainFromMemory:
    """Tests for the train_from_memory function."""

    def test_train_from_memory(self):
        """Training from memory entries should return losses and modify bandit."""
        bandit = ContextualBandit(learning_rate=0.01)
        old_weights_approve = bandit.weights["approve"].copy()

        entries = [
            {
                "current_load_rt": 750.0,
                "predicted_load_rt": 800.0,
                "execution_status": "completed",
                "safety_passed": True,
                "cop_improvement": 0.05,
            },
            {
                "current_load_rt": 500.0,
                "predicted_load_rt": 600.0,
                "execution_status": "aborted",
                "safety_passed": False,
                "cop_improvement": 0.0,
            },
            {
                "current_load_rt": 900.0,
                "predicted_load_rt": 850.0,
                "execution_status": "completed",
                "safety_passed": True,
                "cop_improvement": 0.02,
            },
        ]

        losses = train_from_memory(bandit, entries, epochs=5)

        assert isinstance(losses, list)
        assert len(losses) == 5

        # Weights should change after training
        assert not np.allclose(old_weights_approve, bandit.weights["approve"])

    def test_train_from_memory_empty(self):
        """Training on empty entries should return empty list and not crash."""
        bandit = ContextualBandit()
        losses = train_from_memory(bandit, [], epochs=5)
        assert losses == []


class TestComputeReward:
    """Tests for compute_reward_from_strategy."""

    def test_compute_reward_success_high(self):
        """Successful execution with good COP and energy saving → 1.0."""
        strategy = {
            "expected_cop_improvement": 0.10,
            "expected_energy_saving_kwh_per_h": 50.0,
        }
        reward = compute_reward_from_strategy(strategy, execution_success=True)
        assert reward == 1.0

    def test_compute_reward_success_moderate(self):
        """COP improved but no energy savings → 0.5."""
        strategy = {
            "expected_cop_improvement": 0.03,
            "expected_energy_saving_kwh_per_h": 0.0,
        }
        reward = compute_reward_from_strategy(strategy, execution_success=True)
        assert reward == 0.5

    def test_compute_reward_success_neutral(self):
        """COP improvement near zero → 0.0."""
        strategy = {
            "expected_cop_improvement": -0.02,
            "expected_energy_saving_kwh_per_h": 10.0,
        }
        reward = compute_reward_from_strategy(strategy, execution_success=True)
        assert reward == 0.0

    def test_compute_reward_success_bad(self):
        """Negative COP improvement → -0.5."""
        strategy = {
            "expected_cop_improvement": -0.10,
            "expected_energy_saving_kwh_per_h": 0.0,
        }
        reward = compute_reward_from_strategy(strategy, execution_success=True)
        assert reward == -0.5

    def test_compute_reward_failure(self):
        """Execution failure → -1.0 regardless of other factors."""
        strategy = {
            "expected_cop_improvement": 0.15,
            "expected_energy_saving_kwh_per_h": 100.0,
        }
        reward = compute_reward_from_strategy(strategy, execution_success=False)
        assert reward == -1.0

    def test_compute_reward_default_strategy(self):
        """Default empty strategy with success → 0.5 (cop > 0 is falsy)."""
        strategy = {}
        reward = compute_reward_from_strategy(strategy, execution_success=True)
        # cop_imp is None → 0.0 → goes to elif cop > 0: False → next elif cop > -0.05: True → 0.0
        # Actually {} → cop_imp = None → 0.0 → not > 0 → goes to cop > -0.05 → True → 0.0
        assert reward == 0.0
