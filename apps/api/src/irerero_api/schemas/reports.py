import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from irerero_api.schemas.common import Issue
from irerero_contract.enums import MainProblem, Origin, QualityFlag, ReportChannel


class ReportCountsIn(BaseModel):
    enrolled_0_2_female: int = Field(ge=0, le=999)
    enrolled_0_2_male: int = Field(ge=0, le=999)
    enrolled_3_6_female: int = Field(ge=0, le=999)
    enrolled_3_6_male: int = Field(ge=0, le=999)
    avg_daily_attendance: int = Field(ge=0, le=9999)
    waiting_list: int = Field(ge=0, le=9999)
    caregivers_present: int = Field(ge=0, le=99)
    days_open: int = Field(ge=0, le=6)
    days_meal_served: int = Field(ge=0, le=6)
    referrals_growth_monitoring: int = Field(ge=0, le=999)
    children_with_disability: int = Field(ge=0, le=999)


class ReportIn(ReportCountsIn):
    centre_code: str
    week_start: date
    wash_available: bool
    main_problem: MainProblem
    channel: ReportChannel
    confirmed: bool = Field(
        default=False, description="The reporter has seen the warnings and confirms the values"
    )


class ValidationOut(BaseModel):
    accepted: bool
    errors: list[Issue]
    warnings: list[Issue]
    flags: list[QualityFlag]


class ReportOut(ReportCountsIn):
    id: uuid.UUID
    centre_code: str
    week_start: date
    wash_available: bool
    main_problem: MainProblem
    channel: ReportChannel
    quality_flags: list[QualityFlag]
    submitted_at: datetime
    origin: Origin
