from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class TriggerType(str, Enum):
    SCHEDULED = "scheduled"
    LOAD_CHANGE = "load_change"
    FAULT = "fault"
    PRICE_SIGNAL = "price_signal"
    MANUAL = "manual"


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ABORTED = "aborted"


class StrategyAction(BaseModel):
    seq: int
    device: str
    action: str
    param: Optional[str] = None
    value: Optional[float] = None
    rate: Optional[float] = None
    from_val: Optional[float] = None
    to_val: Optional[float] = None

    @property
    def is_discrete(self) -> bool:
        return self.action in ("start", "stop", "open_valve", "close_valve")

    @property
    def is_continuous(self) -> bool:
        return not self.is_discrete


class TransitionPhase(BaseModel):
    seq: int
    duration_sec: float
    description: str
    actions: List[StrategyAction] = Field(default_factory=list)
    stability_check: Optional[Dict[str, Any]] = None


class TransitionPlan(BaseModel):
    total_duration_sec: float
    phases: List[TransitionPhase]
    abort_conditions: List[str] = Field(default_factory=list)
    rollback_actions: List[StrategyAction] = Field(default_factory=list)


class Strategy(BaseModel):
    strategy_id: str
    trigger_type: TriggerType
    trigger_time: float = 0.0

    # Context
    current_load_rt: float = 0.0
    predicted_load_rt: float = 0.0
    load_ci_lower: Optional[float] = None
    load_ci_upper: Optional[float] = None
    outdoor_wb_temp: float = 26.0
    electricity_price: float = 0.8
    carbon_intensity: float = 0.5

    # Actions
    actions: List[StrategyAction]
    transition_plan: Optional[TransitionPlan] = None

    # Expected effects
    expected_cop_improvement: Optional[float] = None
    expected_energy_saving_kwh_per_h: Optional[float] = None
    expected_carbon_saving_kg_per_h: Optional[float] = None
    expected_cost_saving_yuan_per_h: Optional[float] = None

    # Safety
    preconditions: List[str] = Field(default_factory=list)
    risk_mitigations: List[str] = Field(default_factory=list)

    # Lifecycle
    status: StrategyStatus = StrategyStatus.DRAFT
    llm_reasoning: str = ""

    @model_validator(mode="after")
    def validate_transition_required(self):
        if self.trigger_type in (
            TriggerType.LOAD_CHANGE, TriggerType.SCHEDULED,
            TriggerType.PRICE_SIGNAL, TriggerType.MANUAL,
        ):
            if self.transition_plan is None and len(self.actions) > 0:
                raise ValueError(
                    f"Strategy with trigger_type={self.trigger_type.value} "
                    f"requires a transition_plan"
                )
        return self

    @property
    def is_approved(self) -> bool:
        return self.status == StrategyStatus.APPROVED

    @property
    def is_terminal(self) -> bool:
        return self.status in (StrategyStatus.COMPLETED, StrategyStatus.REJECTED,
                               StrategyStatus.ABORTED)

    def approve(self) -> None:
        if self.status != StrategyStatus.UNDER_REVIEW:
            raise ValueError(f"Cannot approve strategy in status {self.status}")
        self.status = StrategyStatus.APPROVED

    def reject(self, reason: str = "") -> None:
        self.status = StrategyStatus.REJECTED
        if reason:
            self.llm_reasoning += f"\nRejection reason: {reason}"
