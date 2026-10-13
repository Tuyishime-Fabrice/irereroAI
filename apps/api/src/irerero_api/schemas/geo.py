from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from irerero_api.schemas.common import RangeOut
from irerero_contract.enums import AlertSeverity, CandidateKind, CentreType, Origin

P = TypeVar("P")
Detail = Literal["full", "medium", "coarse"]


class Feature[P](BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any]
    properties: P


class FeatureCollection[P](BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature[P]]


class AreaProperties(BaseModel):
    code: str
    name: str
    level: str
    children: RangeOut | None
    stunting_risk: RangeOut | None
    mothers_barrier_share: RangeOut | None
    uncertainty: float | None
    """Relative half-width of the widest interval; the map hatches above 0.15."""
    children_covered: int | None
    children_uncovered: int | None
    overcrowded_centres: int | None
    centres: int
    demand_signals: int
    origin: Origin | None


class CentreProperties(BaseModel):
    code: str
    name: str
    type: CentreType
    capacity: int
    verified: bool
    reliability_score: float
    latest_attendance: int | None
    overcrowded: bool
    alert_severity: AlertSeverity | None
    origin: Origin


class DemandProperties(BaseModel):
    grid_cell: str
    sector_code: str
    empty_searches: int
    centre_requests: int


class SiteProperties(BaseModel):
    id: str
    name: str
    kind: CandidateKind
    sector_code: str
