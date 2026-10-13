import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api import audit
from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import allows, default_area, require_area, require_centre, resolve
from irerero_api.calendar import current_week
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.routes.centres import alert_out
from irerero_api.routes.reports import to_out as report_out
from irerero_api.schemas.centres import (
    AlertAssign,
    AlertDetail,
    AlertOut,
    AlertResolve,
    OfficerOut,
)
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.services.queries import alert_rows
from irerero_contract.enums import AlertStatus, Role
from irerero_contract.tables import Alert, UserAccount, WeeklyReport
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/alerts", tags=["alerts"])
SessionDep = Annotated[Session, Depends(get_session)]
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
Officer = Annotated[Principal, Depends(require_roles(Role.SECTOR_OFFICER, Role.ADMIN))]


def _source(origin: str, week: date) -> SourceRef:
    return SourceRef("alert", "IrereroAI early warning", week.year, origin)


@router.get("", response_model=Envelope[list[AlertOut]])
def list_alerts(
    session: SessionDep,
    principal: Reader,
    area: str | None = None,
    as_of: date | None = None,
    status_filter: AlertStatus | None = None,
) -> Envelope[list[AlertOut]]:
    week = as_of or current_week(get_settings())
    if principal.role is Role.CAREGIVER:
        assert principal.scope_code is not None
        rows = alert_rows(session, week, centre=principal.scope_code)
    else:
        area = area or default_area(principal)
        require_area(session, principal, area)
        rows = alert_rows(session, week, area=area)
    if status_filter is not None:
        rows = [r for r in rows if r.status == status_filter.value]
    return wrap([alert_out(r, week) for r in rows], [_source(r.origin, r.week_start) for r in rows])


def _load(session: Session, principal: Principal, alert_id: uuid.UUID) -> Alert:
    alert = session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown alert")
    require_centre(session, principal, alert.centre_code)
    return alert


def _detail(session: Session, alert_id: uuid.UUID) -> Envelope[AlertDetail]:
    week = current_week(get_settings())
    row = alert_rows(session, week, alert_id=alert_id)[0]
    reports = session.scalars(
        select(WeeklyReport)
        .where(WeeklyReport.centre_code == row.centre_code, WeeklyReport.week_start <= week)
        .order_by(WeeklyReport.week_start)
    ).all()
    data = AlertDetail.model_validate(
        alert_out(row, week).model_dump()
        | {"reports": [report_out(r) for r in reports], "capacity": row.capacity}
    )
    sources = [_source(row.origin, row.week_start)] + [
        SourceRef("weekly_report", r.source, r.reference_year, r.origin) for r in reports
    ]
    return wrap(data, sources)


@router.get("/{alert_id}", response_model=Envelope[AlertDetail])
def alert_detail(
    alert_id: uuid.UUID, session: SessionDep, principal: Reader
) -> Envelope[AlertDetail]:
    _load(session, principal, alert_id)
    return _detail(session, alert_id)


def _change(
    session: Session,
    principal: Principal,
    alert: Alert,
    action: str,
    values: dict[str, object],
    reason: str | None = None,
) -> None:
    before = {key: getattr(alert, key) for key in values}
    for key, value in values.items():
        setattr(alert, key, value)
    audit.record(
        session,
        principal,
        action,
        "alert",
        str(alert.id),
        before=before,
        after=values,
        reason=reason,
    )
    session.flush()


@router.post("/{alert_id}/acknowledge", response_model=Envelope[AlertDetail])
def acknowledge(
    alert_id: uuid.UUID, session: SessionDep, principal: Officer
) -> Envelope[AlertDetail]:
    alert = _load(session, principal, alert_id)
    _change(session, principal, alert, "alert.acknowledge", {"status": AlertStatus.ACKNOWLEDGED})
    return _detail(session, alert_id)


@router.post("/{alert_id}/assign", response_model=Envelope[AlertDetail])
def assign(
    alert_id: uuid.UUID, body: AlertAssign, session: SessionDep, principal: Officer
) -> Envelope[AlertDetail]:
    alert = _load(session, principal, alert_id)
    assignee = session.get(UserAccount, body.user_id)
    chain = resolve(session, centre=alert.centre_code)
    if (
        assignee is None
        or assignee.role is not Role.SECTOR_OFFICER
        or not allows(_as_principal(assignee), chain)
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Assign to an officer for this centre"
        )
    values: dict[str, object] = {"assigned_to": body.user_id}
    if alert.status is AlertStatus.OPEN:
        values["status"] = AlertStatus.ACKNOWLEDGED
    _change(session, principal, alert, "alert.assign", values)
    return _detail(session, alert_id)


@router.post("/{alert_id}/resolve", response_model=Envelope[AlertDetail])
def resolve_alert(
    alert_id: uuid.UUID, body: AlertResolve, session: SessionDep, principal: Officer
) -> Envelope[AlertDetail]:
    if not body.note.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Say what was done")
    alert = _load(session, principal, alert_id)
    _change(
        session,
        principal,
        alert,
        "alert.resolve",
        {"status": AlertStatus.RESOLVED, "resolution_note": body.note.strip()},
        reason=body.note.strip(),
    )
    return _detail(session, alert_id)


def _as_principal(user: UserAccount) -> Principal:
    return Principal(user.id, user.role, user.scope_level, user.scope_code)


officers = APIRouter(prefix="/officers", tags=["alerts"])


@officers.get("", response_model=list[OfficerOut])
def list_officers(session: SessionDep, principal: Officer, centre_code: str) -> list[OfficerOut]:
    """Officers who may be assigned an alert at this centre."""
    chain = require_centre(session, principal, centre_code)
    users = session.scalars(
        select(UserAccount).where(UserAccount.role == Role.SECTOR_OFFICER, UserAccount.is_active)
    ).all()
    return [
        OfficerOut(id=u.id, display_name=u.display_name, scope_code=u.scope_code)
        for u in users
        if allows(_as_principal(u), chain)
    ]
