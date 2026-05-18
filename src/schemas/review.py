from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field


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

    @property
    def is_positive(self) -> bool:
        return self.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL)

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
        rejections = [o for o in opinions if o.is_rejection]
        conditions = [o for o in opinions if o.verdict == ReviewVerdict.CONDITIONAL_APPROVAL]

        if rejections:
            return cls(
                decision="rejected" if len(rejections) >= 2 else "under_debate",
                reasoning=f"{len(rejections)} advocate(s) rejected",
                has_conflict=len(rejections) < 3 and len(rejections) > 0,
                conflicting_parties={o.advocate for o in rejections},
                debate_needed=len(rejections) == 1,
                debate_topic="reliability vs efficiency" if len(rejections) == 1 else "",
            )

        all_conditions = [c for o in conditions for c in o.concerns]
        return cls(
            decision="approved" if not conditions else "approved_with_conditions",
            reasoning="Unanimous approval" if not conditions else f"Approved with {len(conditions)} condition(s)",
            conditions=all_conditions,
            has_conflict=False,
        )
