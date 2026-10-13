from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import forbidden, require_centre
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.schemas.reports import ReportIn, ReportOut, ValidationOut
from irerero_api.services import reports as service
from irerero_contract.enums import ReportChannel, Role
from irerero_contract.tables import WeeklyReport
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/reports", tags=["reports"])
SessionDep = Annotated[Session, Depends(get_session)]
Reporter = Annotated[
    Principal, Depends(require_roles(Role.CAREGIVER, Role.SECTOR_OFFICER, Role.ADMIN))
]
Reader = Annotated[
    Principal,
    Depends(
        require_roles(
            Role.CAREGIVER,
            Role.SECTOR_OFFICER,
            Role.DISTRICT_PLANNER,
            Role.NATIONAL_ANALYST,
            Role.ADMIN,
        )
    ),
]


def _guard(session: Session, principal: Principal, body: ReportIn) -> None:
    require_centre(session, principal, body.centre_code)
    # Officers enter reports on a centre's behalf; only that path may use the assisted channel.
    assisted = body.channel is ReportChannel.ASSISTED
    if assisted != (principal.role is not Role.CAREGIVER):
        raise forbidden("Use the assisted channel only when entering a report for a centre")


def to_out(report: WeeklyReport) -> ReportOut:
    return ReportOut.model_validate(report, from_attributes=True)


@router.post("/check", response_model=ValidationOut)
def check_report(body: ReportIn, session: SessionDep, principal: Reporter) -> ValidationOut:
    """Validate without saving, so the form can explain problems step by step."""
    _guard(session, principal, body)
    return service.to_out(service.check(session, body))


@router.post(
    "",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationOut}, 409: {"description": "Already reported"}},
)
def submit_report(
    body: ReportIn, session: SessionDep, principal: Reporter
) -> ReportOut | JSONResponse:
    _guard(session, principal, body)
    try:
        outcome = service.submit(session, body, principal.id, get_settings())
    except service.DuplicateReportError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "This week is already reported") from error
    except service.WeekOutOfRangeError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a Monday in the last 12 weeks"
        ) from error
    if outcome.report is None:
        return JSONResponse(
            outcome.validation.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return to_out(outcome.report)


@router.get("", response_model=Envelope[list[ReportOut]])
def list_reports(
    centre_code: str, session: SessionDep, principal: Reader, since: date | None = None
) -> Envelope[list[ReportOut]]:
    require_centre(session, principal, centre_code)
    query = select(WeeklyReport).where(WeeklyReport.centre_code == centre_code)
    if since is not None:
        query = query.where(WeeklyReport.week_start >= since)
    reports = session.scalars(query.order_by(WeeklyReport.week_start)).all()
    sources = [SourceRef("weekly_report", r.source, r.reference_year, r.origin) for r in reports]
    return wrap([to_out(r) for r in reports], sources)
