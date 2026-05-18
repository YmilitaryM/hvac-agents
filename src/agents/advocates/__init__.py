"""Advocate Agents — domain-specific strategy reviewers.

Each advocate reviews optimization strategies from its domain perspective
and produces an AdvocateOpinion with a verdict, concerns, and suggestions.
"""

from src.agents.advocates.reliability import (
    ReliabilityAdvocate,
    review_reliability,
)
from src.agents.advocates.efficiency import (
    EfficiencyAdvocate,
    review_efficiency,
)
from src.agents.advocates.compliance import (
    ComplianceAdvocate,
    review_compliance,
)

__all__ = [
    "ReliabilityAdvocate",
    "review_reliability",
    "EfficiencyAdvocate",
    "review_efficiency",
    "ComplianceAdvocate",
    "review_compliance",
]
