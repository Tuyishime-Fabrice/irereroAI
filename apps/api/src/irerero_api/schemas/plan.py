import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from irerero_api.schemas.common import DriverOut, RangeOut, SourceOut
from irerero_contract.enums import (
    Action,
    Origin,
    RecommendationStatus,
    RejectionReason,
    Role,
    Verdict,
)


class WeightsIn(BaseModel):
    """Policy weights. Choosing them is a policy decision, not a technical one."""

    stunting: float = Field(ge=0, le=1)
    readiness: float = Field(ge=0, le=1)
    jobs: float = Field(ge=0, le=1)


class ScenarioIn(BaseModel):
    district_code: str
    name: str = Field(min_length=1, max_length=120)
    budget_rwf: int = Field(gt=0, le=10_000_000_000)
    weights: WeightsIn
    excluded_site_ids: list[str] = Field(default_factory=list)


class SimulateIn(BaseModel):
    district_code: str
    budget_rwf: int = Field(gt=0, le=10_000_000_000)
    weights: WeightsIn
    include_baseline: bool = False


class OutcomesOut(BaseModel):
    """Countable outcomes only. No stunting reduction is estimated or implied."""

    children_reached: RangeOut
    uncovered_remaining: RangeOut
    high_risk_reached: RangeOut
    mothers_under3_reached: RangeOut
    children_supported: float
    cost_rwf: float
    actions: dict[str, int]


class DecisionOut(BaseModel):
    verdict: Verdict
    reason_code: RejectionReason | None
    reason_text: str | None
    edits: dict[str, Any] | None
    user_name: str
    user_role: Role
    created_at: datetime


class RecommendationOut(BaseModel):
    id: uuid.UUID
    rank: int
    action: Action
    site_id: str
    site_name: str
    sector_code: str
    sector_name: str
    centre_code: str | None
    lon: float
    lat: float
    children_reached: RangeOut
    high_risk_children_reached: RangeOut
    mothers_under3_reached: RangeOut
    children_supported: int
    cost: RangeOut
    drivers: list[DriverOut]
    sources: list[SourceOut]
    status: RecommendationStatus
    explanation_en: str
    explanation_rw: str
    decisions: list[DecisionOut]


class ScenarioOut(BaseModel):
    id: uuid.UUID
    district_code: str
    district_name: str
    name: str
    budget_rwf: int
    weights: WeightsIn
    created_at: datetime
    created_by_name: str
    origin: Origin
    optimizer_version: str
    catchment_minutes: int
    recommendations: list[RecommendationOut]
    rejected: list[RecommendationOut]
    outcomes: OutcomesOut
    baseline: OutcomesOut


class ScenarioSummary(BaseModel):
    id: uuid.UUID
    name: str
    budget_rwf: int
    weights: WeightsIn
    created_at: datetime
    created_by_name: str
    approved: int
    rejected: int
    proposed: int


class SimulationOut(BaseModel):
    outcomes: OutcomesOut
    baseline: OutcomesOut | None


class DecisionIn(BaseModel):
    verdict: Verdict
    reason_code: RejectionReason | None = None
    reason_text: str | None = Field(default=None, max_length=1000)
    edits: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _reason_rules(self) -> "DecisionIn":
        if self.verdict is Verdict.REJECT and self.reason_code is None:
            raise ValueError("A rejection needs a reason")
        if self.reason_code is RejectionReason.OTHER and not (self.reason_text or "").strip():
            raise ValueError("Explain the reason in a few words")
        if self.verdict is Verdict.EDIT and not self.edits:
            raise ValueError("An edit needs at least one changed value")
        return self


class DecisionLogRow(BaseModel):
    created_at: datetime
    user_name: str
    user_role: Role
    verdict: Verdict
    reason_code: RejectionReason | None
    reason_text: str | None
    action: Action
    site_name: str
    scenario_name: str


class PlanningDefaults(BaseModel):
    area_code: str
    budget_rwf: int = Field(gt=0, le=10_000_000_000)
    weights: WeightsIn
