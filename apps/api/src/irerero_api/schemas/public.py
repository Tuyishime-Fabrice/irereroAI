from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from irerero_api.schemas.common import PublicCount
from irerero_contract.enums import CentreType, FeeBand, Origin, RunStatus, SourceStatus

AgeBand = Literal["0_2", "3_6"]


class PublicCentre(BaseModel):
    code: str
    name: str
    type: CentreType
    sector_name: str
    lon: float
    lat: float
    distance_km: float | None
    serves_0_2: bool
    serves_3_6: bool
    opening_hours: str
    fee_band: FeeBand
    offers_meals: bool
    offers_growth_monitoring: bool
    disability_inclusive: bool
    capacity: PublicCount
    free_places: PublicCount | None = Field(
        description="From the latest weekly report; null when the centre has not reported"
    )
    verified_at: datetime | None
    origin: Origin


class FindResult(BaseModel):
    centres: list[PublicCentre]
    demand_recorded: bool = Field(
        description="True when the search found nothing and was counted as unmet demand"
    )


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
