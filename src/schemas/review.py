from enum import Enum
from typing import List, Set
from pydantic import BaseModel, Field, computed_field


class ReviewVerdict(str, Enum):
    APPROVE = "approve"
    CONDITIONAL_APPROVAL = "conditional_approval"
    REJECT = "reject"
    ABSTAIN = "abstain"


class AdvocateOpinion(BaseModel):
    advocate: str
    verdict: ReviewVerdict
    concerns: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence: float = 0.5

    @computed_field
    @property
    def is_positive(self) -> bool:
        return self.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL)

    @computed_field
    @property
    def is_rejection(self) -> bool:
        return self.verdict == ReviewVerdict.REJECT


class ArbitrationResult(BaseModel):
    decision: str
    reasoning: str = ""
    conditions: List[str] = Field(default_factory=list)
    has_conflict: bool = False
    conflicting_parties: Set[str] = Field(default_factory=set)
    debate_needed: bool = False
    debate_topic: str = ""

    @classmethod
    def from_opinions(cls, opinions: List[AdvocateOpinion]) -> "ArbitrationResult":
        verdicts = [op.verdict for op in opinions]
        rejections = [op for op in opinions if op.is_rejection]
        has_conflict = any(op.verdict == ReviewVerdict.REJECT for op in opinions) and \
                       any(op.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL) for op in opinions)
        all_approve = all(op.verdict == ReviewVerdict.APPROVE for op in opinions)
        any_reject = any(op.verdict == ReviewVerdict.REJECT for op in opinions)

        if all_approve:
            decision = "approved"
            reasoning = "所有Agent一致通过"
        elif any_reject:
            decision = "rejected"
            reasons = '; '.join(c for op in rejections for c in op.concerns)
            reasoning = f"Agent拒绝 — 理由: {reasons}" if reasons else "Agent拒绝"
        else:
            decision = "conditional_approval"
            reasoning = "有条件通过，需满足附加条件"

        conflicting_parties = {op.advocate for op in opinions if op.is_rejection}

        return cls(
            decision=decision,
            reasoning=reasoning,
            conditions=[c for op in opinions for c in op.concerns],
            has_conflict=has_conflict,
            conflicting_parties=conflicting_parties,
            debate_needed=has_conflict,
            debate_topic="策略安全性辩论" if has_conflict else "",
        )
