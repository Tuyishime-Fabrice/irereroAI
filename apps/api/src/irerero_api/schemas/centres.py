import uuid
from datetime import date, datetime

from pydantic import BaseModel

from irerero_api.schemas.reports import ReportOut
from irerero_contract.enums import (
    AlertKind,
    AlertSeverity,
    AlertStatus,
    CentreStatus,
    CentreType,
    FeeBand,
    Origin,
)


class CentreRow(BaseModel):
    code: str
    name: str
    type: CentreType
    status: CentreStatus
    sector_code: str
    sector_name: str
    capacity: int
    verified: bool
    verified_at: datetime | None
    reliability_score: float
    last_report_week: date | None
    reported_this_week: bool
    latest_enrolled: int | None
    latest_attendance: int | None
    open_alerts: int
    lon: float
    lat: float
    origin: Origin


class AlertOut(BaseModel):
    id: uuid.UUID
    centre_code: str
    centre_name: str
    sector_code: str
    sector_name: str
    week_start: date
    kind: AlertKind
    severity: AlertSeverity
    reason_en: str
    reason_rw: str
    evidence: dict[str, float | int | str]
    status: AlertStatus
    assigned_to: uuid.UUID | None
    assigned_name: str | None
    resolution_note: str | None
    age_weeks: int
    origin: Origin


class CentreDetail(CentreRow):
    opening_hours: str
    fee_band: FeeBand
    serves_0_2: bool
    serves_3_6: bool
    offers_meals: bool
    offers_growth_monitoring: bool
    disability_inclusive: bool
    ncda_ref: str | None
    reports: list[ReportOut]
    alerts: list[AlertOut]


class AlertDetail(AlertOut):
    reports: list[ReportOut]
    capacity: int


class AlertAssign(BaseModel):
    user_id: uuid.UUID


class AlertResolve(BaseModel):
    note: str


class OfficerOut(BaseModel):
    id: uuid.UUID
    display_name: str
    scope_code: str | None
