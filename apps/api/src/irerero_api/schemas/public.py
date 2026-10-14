from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from irerero_api.schemas.common import PublicCount
from irerero_contract.enums import CentreType, Origin, RunStatus, SourceStatus

AgeBand = Literal["0_2", "3_6"]


class PublicCentre(BaseModel):
    code: str
    name: str
    type: CentreType
    sector_name: str
    lon: float
    lat: float
    distance_km: float
    walking_minutes: int = Field(description="Estimated from straight-line distance")
    serves_0_2: bool
    serves_3_6: bool
    offers_meals: bool
    capacity: PublicCount
    free_places: PublicCount = Field(description="Capacity minus enrolment from the centre feed")
    origin: Origin


class DemandRequest(BaseModel):
    lon: float = Field(ge=28.8, le=31.0)
    lat: float = Field(ge=-2.9, le=-1.0)
    age_band: AgeBand | None = None


class DemandRecorded(BaseModel):
    grid_cell: str
    sector_name: str


class DataSourceOut(BaseModel):
    id: str
    name: str
    publisher: str
    reference_year: int | None
    origin: Origin
    status: SourceStatus
    licence: str
    url: str | None
    feeds: list[str]


class CheckOut(BaseModel):
    name: str
    passed: bool
    detail: str


class PipelineRunOut(BaseModel):
    id: str
    pipeline: str
    origin: Origin
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    code_version: str
    row_counts: dict[str, int]
    checks: list[CheckOut]


class Methodology(BaseModel):
    sources: list[DataSourceOut]
    runs: list[PipelineRunOut]


class Place(BaseModel):
    code: str
    name: str
    lon: float
    lat: float


class District(Place):
    sectors: list[Place]
