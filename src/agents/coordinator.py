"""Coordinator Agent — arbitrates advocate opinions and manages debates.

The Coordinator sits between advocate review and execution. It takes
AdvocateOpinions, applies weighted voting, detects conflicts, and either
approves the strategy or triggers a debate between conflicting advocates.

Core logic is in arbitrate() and run_debate_round() — pure Python, no LLM.
"""

import random
from typing import Any, Dict, List, Optional, Tuple

from src.agents.base import BaseAgent
from src.schemas.review import AdvocateOpinion, ArbitrationResult, ReviewVerdict

# --- Advocate weights for weighted voting ---
ADVOCATE_WEIGHTS: Dict[str, float] = {
    "reliability": 1.5,  # safety-critical
    "efficiency": 1.0,
    "compliance": 1.2,  # regulatory
}

DEFAULT_MAX_DEBATE_ROUNDS = 2


def _compute_weighted_score(opinions: List[AdvocateOpinion]) -> float:
    """Compute a weighted score from opinions.

    APPROVE = +1, CONDITIONAL_APPROVAL = +0.5, ABSTAIN = 0, REJECT = -1.
    Each opinion is weighted by its advocate's weight and confidence.
    """
    score = 0.0
    total_weight = 0.0
    for op in opinions:
        w = ADVOCATE_WEIGHTS.get(op.advocate, 1.0)
        if op.verdict == ReviewVerdict.APPROVE:
            s = 1.0
        elif op.verdict == ReviewVerdict.CONDITIONAL_APPROVAL:
            s = 0.5
        elif op.verdict == ReviewVerdict.ABSTAIN:
            s = 0.0
        else:  # REJECT
            s = -1.0
        score += w * op.confidence * s
        total_weight += w * op.confidence
    if total_weight > 0:
        return score / total_weight
    return 0.0


def arbitrate(
    opinions: List[AdvocateOpinion],
    strategy: Optional[Any] = None,
) -> ArbitrationResult:
    """Arbitrate between advocate opinions to reach a decision.

    Uses weighted voting with conflict detection:

    - reliability has weight 1.5 (safety-critical)
    - efficiency has weight 1.0
    - compliance has weight 1.2 (regulatory)

    Decision rules:
    - 2+ REJECT -> "rejected"
    - 1 REJECT -> "under_debate" (triggers debate, not auto-rejected)
    - Any CONDITIONAL_APPROVAL -> "approved_with_conditions"
    - All APPROVE/ABSTAIN -> "approved"
    - ABSTAIN opinions are ignored in counting
    """
    active_opinions = [o for o in opinions if o.verdict != ReviewVerdict.ABSTAIN]

    if not active_opinions:
        return ArbitrationResult(
            decision="approved",
            reasoning="All advocates abstained — defaulting to approval",
            has_conflict=False,
        )

    rejections = [o for o in active_opinions if o.verdict == ReviewVerdict.REJECT]
    cond_advocates = [
        o for o in active_opinions if o.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
    ]

    # Build reasoning with weighted score context
    weighted_score = _compute_weighted_score(active_opinions)
    weight_detail = ", ".join(
        f"{op.advocate}={ADVOCATE_WEIGHTS.get(op.advocate, 1.0)}"
        for op in active_opinions
    )

    # 2+ rejections -> rejected
    if len(rejections) >= 2:
        rejecting_names = sorted(o.advocate for o in rejections)
        return ArbitrationResult(
            decision="rejected",
            reasoning=(
                f"{len(rejections)} advocates rejected "
                f"({', '.join(rejecting_names)}). "
                f"Weighted score: {weighted_score:.2f}. "
                f"Weights: {weight_detail}"
            ),
            has_conflict=True,
            conflicting_parties=set(rejecting_names),
            debate_needed=False,
        )

    # Single rejection -> under_debate
    if len(rejections) == 1:
        rej = rejections[0]
        others = sorted(o.advocate for o in active_opinions if o != rej)
        topic = f"{rej.advocate} rejected vs {', '.join(others)}"
        return ArbitrationResult(
            decision="under_debate",
            reasoning=(
                f"{rej.advocate} (weight={ADVOCATE_WEIGHTS.get(rej.advocate, 1.0)})"
                f" rejected. Weighted score: {weighted_score:.2f}. "
                f"Weights: {weight_detail}"
            ),
            has_conflict=True,
            conflicting_parties={rej.advocate, *others},
            debate_needed=True,
            debate_topic=topic,
        )

    # Conditional approvals -> approved_with_conditions
    if cond_advocates:
        all_concerns: List[str] = []
        for ca in cond_advocates:
            all_concerns.extend(ca.concerns)
        cond_names = sorted(o.advocate for o in cond_advocates)
        return ArbitrationResult(
            decision="approved_with_conditions",
            reasoning=(
                f"Approved with {len(all_concerns)} condition(s) "
                f"from {', '.join(cond_names)}. "
                f"Weighted score: {weighted_score:.2f}. "
                f"Weights: {weight_detail}"
            ),
            conditions=all_concerns,
            has_conflict=False,
        )

    # All approve
    return ArbitrationResult(
        decision="approved",
        reasoning=(
            f"All advocates approve. "
            f"Weighted score: {weighted_score:.2f}. "
            f"Weights: {weight_detail}"
        ),
        has_conflict=False,
    )


def run_debate_round(
    opinions: List[AdvocateOpinion],
    debate_state: Dict[str, Any],
    strategy: Optional[Any] = None,
) -> Tuple[List[AdvocateOpinion], Dict[str, Any]]:
    """Run one round of debate between conflicting advocates.

    Simulates a debate round where conflicting advocates reconsider
    based on each other's concerns. In a real system, this would use LLM.

    For now, it's a deterministic simulation:
    - If current_round >= max_rounds, finalize with current opinions
    - Otherwise, conflicting advocates lower their confidence slightly
    - If only one objector and others approve, objector may concede (50% chance)
    - Debate round increments

    Args:
        opinions: Current advocate opinions.
        debate_state: Current debate state dict (compatible with InvestDebateState).
        strategy: The strategy under debate (optional, for context).

    Returns:
        (updated_opinions, updated_debate_state)
    """
    current_round = debate_state.get("current_round", 0)
    max_rounds = debate_state.get("max_rounds", DEFAULT_MAX_DEBATE_ROUNDS)

    new_state = dict(debate_state)

    # Already at or past max rounds — finalize
    if current_round >= max_rounds:
        new_state["consensus_reached"] = True
        new_state["final_verdict"] = _determine_final_verdict(opinions)
        new_state["opinions"] = [o.model_dump() for o in opinions]
        return opinions, new_state

    active = [o for o in opinions if o.verdict != ReviewVerdict.ABSTAIN]
    rejections = [o for o in active if o.verdict == ReviewVerdict.REJECT]
    approves = [o for o in active if o.verdict == ReviewVerdict.APPROVE]

    # If single objector + others approve: 50% chance objector concedes
    if len(rejections) == 1 and len(approves) >= 2:
        if random.random() < 0.5:
            # Objector concedes: change REJECT to CONDITIONAL_APPROVAL
            updated_opinions = []
            for op in opinions:
                if op.verdict == ReviewVerdict.REJECT:
                    new_op = AdvocateOpinion(
                        advocate=op.advocate,
                        verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
                        concerns=op.concerns,
                        suggestions=op.suggestions or [
                            f"Conceded after debate round {current_round + 1}"
                        ],
                        confidence=max(0.1, op.confidence - 0.2),
                    )
                    updated_opinions.append(new_op)
                else:
                    updated_opinions.append(op)
            new_state["consensus_reached"] = True
            new_state["final_verdict"] = "conditional_approval"
            new_state["current_round"] = current_round + 1
            new_state["opinions"] = [o.model_dump() for o in updated_opinions]
            return updated_opinions, new_state

    # Otherwise: reduce confidence of conflicting advocates
    updated_opinions = []
    for op in opinions:
        if op.verdict == ReviewVerdict.REJECT:
            updated_opinions.append(
                AdvocateOpinion(
                    advocate=op.advocate,
                    verdict=op.verdict,
                    concerns=op.concerns,
                    suggestions=op.suggestions,
                    confidence=max(0.05, op.confidence - 0.1),
                )
            )
        else:
            updated_opinions.append(op)

    new_state["current_round"] = current_round + 1
    new_state["opinions"] = [o.model_dump() for o in updated_opinions]

    # Check if we've now reached max rounds
    if new_state["current_round"] >= max_rounds:
        new_state["consensus_reached"] = True
        new_state["final_verdict"] = _determine_final_verdict(updated_opinions)

    return updated_opinions, new_state


def _determine_final_verdict(opinions: List[AdvocateOpinion]) -> str:
    """Determine the final verdict from a set of opinions after debate."""
    active = [o for o in opinions if o.verdict != ReviewVerdict.ABSTAIN]
    if not active:
        return "approved"
    rejections = [o for o in active if o.verdict == ReviewVerdict.REJECT]
    if len(rejections) >= 2:
        return "rejected"
    if rejections:
        return "under_debate"
    conds = [o for o in active if o.verdict == ReviewVerdict.CONDITIONAL_APPROVAL]
    if conds:
        return "conditional_approval"
    return "approved"


class CoordinatorAgent(BaseAgent):
    """Coordinates the review process, arbitrates advocate opinions, and manages debates.

    This agent sits between the advocate review layer and the safety/execution
    layer. It takes advocate opinions, arbitrates them into a decision, and
    manages debates when there are conflicts.

    Core logic is in arbitrate() and run_debate_round().

    Optional RL bandit: when provided, the bandit can override the arbitration
    decision when confidence exceeds the configured threshold. Safety gates run
    first to enforce hard constraints, then RL can influence the decision.
    """

    def __init__(self, llm=None, context=None, bandit=None):
        super().__init__(name="coordinator", llm=llm, context=context)
        self.bandit = bandit

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordination: arbitrate opinions, trigger debate if needed.

        Args:
            input_data: dict with:
                - advocate_opinions: List[Dict] serialized AdvocateOpinions
                - pending_strategy: Strategy object or dict (optional)
                - max_debate_rounds: int (optional, default 2)

        Returns:
            dict with arbitration_result, debate_state, final_opinions.
        """
        # Parse opinions
        opinions_data = input_data.get("advocate_opinions", [])
        opinions: List[AdvocateOpinion] = []
        for o in opinions_data:
            if isinstance(o, AdvocateOpinion):
                opinions.append(o)
            elif isinstance(o, dict):
                opinions.append(
                    AdvocateOpinion(
                        advocate=o.get("advocate", ""),
                        verdict=ReviewVerdict(o.get("verdict", "abstain")),
                        concerns=o.get("concerns", []),
                        suggestions=o.get("suggestions", []),
                        confidence=o.get("confidence", 0.5),
                    )
                )

        # Parse strategy (optional)
        strategy = input_data.get("pending_strategy")
        if strategy is not None and isinstance(strategy, dict):
            from src.schemas.strategy import Strategy

            strategy = Strategy(**strategy)

        # Arbitrate
        result = arbitrate(opinions, strategy)

        # Trigger debate if needed
        debate_state: Optional[Dict[str, Any]] = None
        if result.debate_needed:
            max_rounds = input_data.get("max_debate_rounds", DEFAULT_MAX_DEBATE_ROUNDS)
            debate_state = {
                "strategy_id": strategy.strategy_id if strategy else "",
                "topic": result.debate_topic,
                "current_round": 0,
                "opinions": [o.model_dump() for o in opinions],
                "consensus_reached": False,
                "final_verdict": "",
                "max_rounds": max_rounds,
            }
            opinions, debate_state = run_debate_round(opinions, debate_state, strategy)
            result = arbitrate(opinions, strategy)

        # Optional RL bandit override
        rl_override = None
        if self.bandit is not None and strategy is not None:
            try:
                from src.rl.features import extract_features
                from src.rl.safety_gates import check_rl_safety_gates
                from src.config import get_config

                features = extract_features(strategy)
                gate_result = check_rl_safety_gates(
                    features, result.decision, strategy.model_dump()
                )

                if gate_result.get("blocked"):
                    rl_override = {
                        "source": "rl_safety_gate",
                        "original": result.decision,
                        "override": gate_result.get("action", result.decision),
                        "reason": gate_result.get("reason", ""),
                    }
                else:
                    action, confidence = self.bandit.predict(features)
                    threshold = get_config().rl.confidence_threshold
                    if confidence >= threshold:
                        rl_override = {
                            "source": "rl_bandit",
                            "original": result.decision,
                            "override": "approved" if action == 1 else "rejected",
                            "confidence": confidence,
                        }
            except ImportError:
                self.logger.warning("RL override unavailable (missing module), using rule-based decision")
            except Exception:
                self.logger.warning(
                    "RL override failed for strategy %s, using rule-based decision",
                    getattr(strategy, 'strategy_id', 'unknown'),
                    exc_info=True,
                )

        return {
            "arbitration_result": result.model_dump(),
            "debate_state": debate_state,
            "final_opinions": [o.model_dump() for o in opinions],
            "rl_override": rl_override,
        }
