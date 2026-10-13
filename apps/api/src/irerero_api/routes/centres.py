from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from irerero_api import audit
from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import default_area, require_area, require_centre
from irerero_api.calendar import current_week
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.routes.reports import to_out as report_out
from irerero_api.schemas.centres import AlertOut, CentreDetail, CentreRow
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.services.queries import alert_rows, centre_rows
from irerero_contract.enums import Role
from irerero_contract.tables import Centre, WeeklyReport
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/centres", tags=["centres"])
SessionDep = Annotated[Session, Depends(get_session)]
Staff = Annotated[
    Principal,
    Depends(
        require_roles(Role.SECTOR_OFFICER, Role.DISTRICT_PLANNER, Role.NATIONAL_ANALYST, Role.ADMIN)
    ),
]
AnyReader = Annotated[
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
Officer = Annotated[Principal, Depends(require_roles(Role.SECTOR_OFFICER, Role.ADMIN))]


def row_out(row: Row[Any]) -> CentreRow:
    return CentreRow.model_validate(row._mapping)


def alert_out(row: Row[Any], week: date) -> AlertOut:
    m = dict(row._mapping)
    m["age_weeks"] = max(0, (week - m["week_start"]).days // 7)
    return AlertOut.model_validate(m)


def centre_source(row: Row[Any]) -> SourceRef:
    return SourceRef("centre", row.source, row.reference_year, row.origin)


@router.get("", response_model=Envelope[list[CentreRow]])
def list_centres(
    session: SessionDep, principal: Staff, area: str | None = None, week: date | None = None
) -> Envelope[list[CentreRow]]:
    area = area or default_area(principal)
    require_area(session, principal, area)
    rows = centre_rows(session, week or current_week(get_settings()), area=area)
    return wrap([row_out(r) for r in rows], [centre_source(r) for r in rows])


def detail(session: Session, code: str, week: date) -> Envelope[CentreDetail]:
    rows = centre_rows(session, week, code=code)
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown centre")
    row = rows[0]
    reports = session.scalars(
        select(WeeklyReport)
        .where(WeeklyReport.centre_code == code, WeeklyReport.week_start <= week)
        .order_by(WeeklyReport.week_start)
    ).all()
    alerts = [alert_out(a, week) for a in alert_rows(session, week, centre=code)]
    data = CentreDetail.model_validate(
        dict(row._mapping) | {"reports": [report_out(r) for r in reports], "alerts": alerts}
    )
    sources = [centre_source(row)] + [
        SourceRef("weekly_report", r.source, r.reference_year, r.origin) for r in reports
    ]
    return wrap(data, sources)


@router.get("/{code}", response_model=Envelope[CentreDetail])
def centre_detail(
    code: str, session: SessionDep, principal: AnyReader, week: date | None = None
) -> Envelope[CentreDetail]:
    require_centre(session, principal, code)
    return detail(session, code, week or current_week(get_settings()))


class VerifyIn(BaseModel):
    note: str | None = None


@router.post("/{code}/verify", response_model=Envelope[CentreDetail])
def verify_centre(
    code: str, body: VerifyIn, session: SessionDep, principal: Officer
) -> Envelope[CentreDetail]:
    """Record that an officer checked the centre in person."""
    require_centre(session, principal, code)
    centre = session.get(Centre, code)
    assert centre is not None
    before = {"verified": centre.verified, "verified_at": centre.verified_at}
    centre.verified = True
    centre.verified_at = datetime.now(UTC)
    centre.verified_by = principal.id
    audit.record(
        session,
        principal,
        "centre.verify",
        "centre",
        code,
        before=before,
        after={"verified": True, "verified_at": centre.verified_at},
        reason=body.note,
    )
    session.flush()
    return detail(session, code, current_week(get_settings()))
