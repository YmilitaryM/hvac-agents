"""Offline trainer for the contextual bandit using MemoryLog entries."""

from typing import List, Optional
import numpy as np

from .bandit import ContextualBandit, TrainingExample
from .features import extract_features


def build_training_examples(
    memory_entries: List[dict],
) -> List[TrainingExample]:
    """Convert MemoryLog entries (as dicts) into training examples.

    Reward signal:
      +1.0  : execution completed, safety passed, COP improved
      +0.5  : execution completed, safety passed, no COP change
      -0.5  : execution completed, safety failed
      -1.0  : execution aborted

    For "approve" action (the strategy was approved and executed):
      reward = actual outcome

    For "reject" action (we imagine what would happen):
      We don't have counterfactuals, so we only create "approve" examples
      from actually-executed strategies. Strategies that were rejected
      by the coordinator don't reach execution.
    """
    examples = []

    for entry in memory_entries:
        features = extract_features(
            current_load_rt=entry.get("current_load_rt", 0),
            predicted_load_rt=entry.get("predicted_load_rt", 0),
            electricity_price=entry.get("electricity_price", 0.8),
            carbon_intensity=entry.get("carbon_intensity", 0.5),
        )

        status = entry.get("execution_status", "aborted")
        safety_passed = entry.get("safety_passed", False)
        cop_improvement = entry.get("cop_improvement") or 0.0

        if status == "completed" and safety_passed:
            if cop_improvement > 0.01:
                reward = 1.0
            elif cop_improvement > -0.01:
                reward = 0.5
            else:
                reward = -0.5
        elif status == "completed" and not safety_passed:
            reward = -0.5
        else:  # aborted
            reward = -1.0

        examples.append(TrainingExample(
            features=features,
            action_taken="approve",  # this strategy was approved
            reward=reward,
        ))

    return examples


def train_from_memory(
    bandit: ContextualBandit,
    memory_entries: List[dict],
    epochs: int = 10,
) -> List[float]:
    """Train the bandit from MemoryLog entries.

    Args:
        bandit: The ContextualBandit to train.
        memory_entries: List of MemoryEntry dicts from MemoryLog.to_dict_list().
        epochs: Number of training epochs.

    Returns:
        List of average losses per epoch.
    """
    examples = build_training_examples(memory_entries)
    if not examples:
        return []
    return bandit.train_batch(examples, epochs=epochs)


def compute_reward_from_strategy(
    strategy: dict,
    actual_cop: Optional[float] = None,
    execution_success: bool = True,
) -> float:
    """Compute the reward signal for a strategy execution.

    This can be called after execution to create a new training example.
    """
    if not execution_success:
        return -1.0

    cop_imp = strategy.get("expected_cop_improvement") or 0.0
    energy_saving = strategy.get("expected_energy_saving_kwh_per_h") or 0.0

    if cop_imp > 0.05 and energy_saving > 0:
        return 1.0
    elif cop_imp > 0:
        return 0.5
    elif cop_imp > -0.05:
        return 0.0
    else:
        return -0.5
