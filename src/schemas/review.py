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
