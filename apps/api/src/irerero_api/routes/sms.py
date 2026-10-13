"""SMS report simulator. Phase 1 has no gateway; the caregiver app posts the message text here."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import require_centre
from irerero_api.calendar import current_week
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.reports import ReportIn, ValidationOut
from irerero_api.services import reports as service
from irerero_api.services import sms
from irerero_contract.enums import ReportChannel, Role

router = APIRouter(prefix="/sms", tags=["sms"])
SessionDep = Annotated[Session, Depends(get_session)]
Caregiver = Annotated[Principal, Depends(require_roles(Role.CAREGIVER))]


class SmsIn(BaseModel):
    text: str


class SmsResult(BaseModel):
    status: Literal["saved", "needs_confirmation", "rejected", "duplicate", "format_error"]
    format_error: str | None = None
    format_detail: str | None = None
    parsed: ReportIn | None = None
    validation: ValidationOut | None = None


class SmsFormat(BaseModel):
    example: str
    fields: list[str]
    problems: list[str]


@router.get("/format", response_model=SmsFormat)
def sms_format(principal: Caregiver) -> SmsFormat:
    centre = principal.scope_code or "ECD-CODE"
    return SmsFormat(
        example=sms.example(centre, current_week(get_settings())),
        fields=[
            "centre",
            "week",
            *sms.COUNT_ORDER,
            "wash_available",
            *sms.TAIL_ORDER,
            "main_problem",
        ],
        problems=[p.value for p in sms.PROBLEMS],
    )


@router.post("/simulate", response_model=SmsResult)
def simulate(body: SmsIn, session: SessionDep, principal: Caregiver) -> SmsResult:
    settings = get_settings()
    try:
        parsed = sms.parse(body.text, current_week(settings))
    except sms.SmsFormatError as error:
        return SmsResult(status="format_error", format_error=error.code, format_detail=error.detail)
    report = ReportIn(
        centre_code=parsed.centre_code,
        week_start=parsed.week_start,
        wash_available=parsed.wash_available,
        main_problem=parsed.main_problem,
        channel=ReportChannel.SMS,
        confirmed=parsed.confirmed,
        **parsed.counts,
    )
    require_centre(session, principal, report.centre_code)
    try:
        outcome = service.submit(session, report, principal.id, settings)
    except service.DuplicateReportError:
        return SmsResult(status="duplicate", parsed=report)
    except service.WeekOutOfRangeError:
        return SmsResult(status="format_error", format_error="bad_week", parsed=report)
    if outcome.report is not None:
        return SmsResult(status="saved", parsed=report, validation=outcome.validation)
    state = "rejected" if outcome.validation.errors else "needs_confirmation"
    return SmsResult(status=state, parsed=report, validation=outcome.validation)
