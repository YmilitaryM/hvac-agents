"""Contextual Bandit for strategy approval/rejection decisions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .features import extract_features, FEATURE_DIM


@dataclass
class BanditPrediction:
    """Result of a bandit prediction."""
    action: str  # "approve" or "reject"
    confidence: float  # 0.0 - 1.0
    score_approve: float  # estimated reward for approving
    score_reject: float  # estimated reward for rejecting
    features: Optional[np.ndarray] = None


@dataclass
class TrainingExample:
    """A single training example for the bandit."""
    features: np.ndarray  # shape (FEATURE_DIM,)
    action_taken: str  # "approve" or "reject"
    reward: float  # observed reward (1.0 = good outcome, -1.0 = bad, 0.0 = neutral)


class ContextualBandit:
    """Linear contextual bandit with ε-greedy exploration.

    Maintains two weight vectors (one for "approve", one for "reject").
    Predicts expected reward as dot(features, weights[action]).
    """

    def __init__(self, epsilon: float = 0.1, learning_rate: float = 0.01):
        self.epsilon = epsilon  # exploration rate
        self.learning_rate = learning_rate

        # Weight vectors for each action, initialized with small random values
        rng = np.random.RandomState(42)
        self.weights: Dict[str, np.ndarray] = {
            "approve": rng.normal(0, 0.1, FEATURE_DIM).astype(np.float64),
            "reject": rng.normal(0, 0.1, FEATURE_DIM).astype(np.float64),
        }

        self.training_history: List[TrainingExample] = []

    def predict(self, features: np.ndarray) -> BanditPrediction:
        """Predict the best action and its confidence.

        Confidence is calculated as the absolute difference between
        approve and reject scores, mapped to [0, 1].
        """
        features = np.asarray(features, dtype=np.float64).flatten()

        score_approve = float(np.dot(self.weights["approve"], features))
        score_reject = float(np.dot(self.weights["reject"], features))

        # ε-greedy: explore with probability epsilon
        if np.random.random() < self.epsilon:
            action = np.random.choice(["approve", "reject"])
        else:
            action = "approve" if score_approve >= score_reject else "reject"

        # Confidence: sigmoid of score difference
        diff = abs(score_approve - score_reject)
        confidence = 1.0 / (1.0 + np.exp(-diff))  # sigmoid, range ~[0.5, 1.0)

        return BanditPrediction(
            action=action,
            confidence=confidence,
            score_approve=score_approve,
            score_reject=score_reject,
            features=features,
        )

    def update(self, features: np.ndarray, action: str, reward: float) -> None:
        """Update weights based on observed reward.

        Uses stochastic gradient descent: w += lr * (reward - prediction) * features
        """
        features = np.asarray(features, dtype=np.float64).flatten()
        predicted = float(np.dot(self.weights[action], features))
        error = reward - predicted
        self.weights[action] += self.learning_rate * error * features

        self.training_history.append(TrainingExample(
            features=features.copy(),
            action_taken=action,
            reward=reward,
        ))

    def train_batch(self, examples: List[TrainingExample], epochs: int = 5) -> List[float]:
        """Train on a batch of examples for multiple epochs.

        Returns list of average losses per epoch.
        """
        losses = []
        for _ in range(epochs):
            epoch_loss = 0.0
            for ex in examples:
                features = np.asarray(ex.features, dtype=np.float64).flatten()
                predicted = float(np.dot(self.weights[ex.action_taken], features))
                error = ex.reward - predicted
                self.weights[ex.action_taken] += self.learning_rate * error * features
                epoch_loss += error ** 2
            losses.append(epoch_loss / max(1, len(examples)))
        return losses

    def get_weights(self) -> Dict[str, List[float]]:
        """Return weights as serializable dict."""
        return {
            "approve": self.weights["approve"].tolist(),
            "reject": self.weights["reject"].tolist(),
        }

    def load_weights(self, weights: Dict[str, List[float]]) -> None:
        """Load weights from a serialized dict."""
        self.weights["approve"] = np.array(weights["approve"], dtype=np.float64)
        self.weights["reject"] = np.array(weights["reject"], dtype=np.float64)
