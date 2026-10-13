import uuid
from datetime import datetime
from typing import Annotated, Any

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api import audit
from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.tokens import revoke_all
from irerero_api.db import get_session
from irerero_api.phone import normalise_phone
from irerero_contract.enums import Role, ScopeLevel
from irerero_contract.passwords import hash_secret
from irerero_contract.tables import AdminUnit, AuditLog, Centre, PipelineRun, UserAccount

router = APIRouter(prefix="/admin", tags=["admin"])
SessionDep = Annotated[Session, Depends(get_session)]
Admin = Annotated[Principal, Depends(require_roles(Role.ADMIN))]
SCOPE_FOR_ROLE = {
    Role.PARENT: ScopeLevel.NONE,
    Role.CAREGIVER: ScopeLevel.CENTRE,
    Role.SECTOR_OFFICER: ScopeLevel.SECTOR,
    Role.DISTRICT_PLANNER: ScopeLevel.DISTRICT,
    Role.NATIONAL_ANALYST: ScopeLevel.NATIONAL,
    Role.ADMIN: ScopeLevel.NATIONAL,
}


class UserOut(BaseModel):
    id: uuid.UUID
    role: Role
    scope_level: ScopeLevel
    scope_code: str | None
    display_name: str
    email: str | None
    phone: str | None
    is_active: bool
    has_totp: bool
    created_at: datetime


class UserIn(BaseModel):
    role: Role
    scope_code: str | None = None
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=12)


class UserCreated(BaseModel):
    user: UserOut
    totp_secret: str | None = Field(description="Shown once, for admins to add to their app")


class UserPatch(BaseModel):
    role: Role | None = None
    scope_code: str | None = None
    display_name: str | None = None
    is_active: bool | None = None


def _out(user: UserAccount) -> UserOut:
    return UserOut(
        id=user.id,
        role=user.role,
        scope_level=user.scope_level,
        scope_code=user.scope_code,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        has_totp=user.totp_secret is not None,
        created_at=user.created_at,
    )


def _check_scope(
    session: Session, role: Role, scope_code: str | None
) -> tuple[ScopeLevel, str | None]:
    level = SCOPE_FOR_ROLE[role]
    if level in (ScopeLevel.NONE, ScopeLevel.NATIONAL):
        return level, None
    if scope_code is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"A {role.value} needs a {level.value}"
        )
    if level is ScopeLevel.CENTRE:
        if session.get(Centre, scope_code) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown centre")
    else:
        unit = session.get(AdminUnit, scope_code)
        if unit is None or unit.level.value != level.value:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Choose a {level.value}")
    return level, scope_code


@router.get("/users", response_model=list[UserOut])
def list_users(session: SessionDep, principal: Admin) -> list[UserOut]:
    users = session.scalars(
        select(UserAccount)
        .where(UserAccount.role != Role.PARENT)
        .order_by(UserAccount.role, UserAccount.display_name)
    ).all()
    return [_out(u) for u in users]


@router.post("/users", response_model=UserCreated, status_code=status.HTTP_201_CREATED)
def create_user(body: UserIn, session: SessionDep, principal: Admin) -> UserCreated:
    level, scope = _check_scope(session, body.role, body.scope_code)
    staff = body.role not in (Role.PARENT, Role.CAREGIVER)
    if staff and (not body.email or not body.password):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Staff need an email and a password"
        )
    phone = normalise_phone(body.phone) if body.phone else None
    if body.role is Role.CAREGIVER and phone is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Caregivers need a mobile number"
        )
    secret = pyotp.random_base32() if body.role is Role.ADMIN else None
    user = UserAccount(
        role=body.role,
        scope_level=level,
        scope_code=scope,
        display_name=body.display_name,
        email=body.email.strip().lower() if body.email else None,
        phone=phone,
        password_hash=hash_secret(body.password) if staff and body.password else None,
        totp_secret=secret,
    )
    session.add(user)
    session.flush()
    audit.record(
        session,
        principal,
        "user.create",
        "user_account",
        str(user.id),
        after={"role": user.role, "scope_code": scope, "display_name": user.display_name},
    )
    return UserCreated(user=_out(user), totp_secret=secret)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID, body: UserPatch, session: SessionDep, principal: Admin
) -> UserOut:
    user = session.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown user")
    if user.id == principal.id and (
        body.is_active is False or (body.role and body.role is not Role.ADMIN)
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "You cannot remove your own admin access"
        )
    before: dict[str, Any] = {
        "role": user.role,
        "scope_code": user.scope_code,
        "is_active": user.is_active,
    }
    role = body.role or user.role
    if body.role is not None or body.scope_code is not None:
        level, scope = _check_scope(
            session, role, body.scope_code if body.scope_code is not None else user.scope_code
        )
        user.role, user.scope_level, user.scope_code = role, level, scope
        if role is Role.ADMIN and user.totp_secret is None:
            user.totp_secret = pyotp.random_base32()
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active
    # A role or scope change takes effect at once: existing sessions end.
    revoke_all(session, user.id)
    audit.record(
        session,
        principal,
        "user.update",
        "user_account",
        str(user.id),
        before=before,
        after={"role": user.role, "scope_code": user.scope_code, "is_active": user.is_active},
    )
    return _out(user)


class AuditOut(BaseModel):
    id: int
    actor_id: uuid.UUID | None
    actor_name: str | None
    actor_role: Role
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    created_at: datetime


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    session: SessionDep,
    principal: Admin,
    action: str | None = None,
    actor_role: Role | None = None,
    entity_type: str | None = None,
    since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[AuditOut]:
    query = select(AuditLog, UserAccount.display_name).outerjoin(
        UserAccount, UserAccount.id == AuditLog.actor_id
    )
    if action:
        query = query.where(AuditLog.action.startswith(action))
    if actor_role:
        query = query.where(AuditLog.actor_role == actor_role)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if since:
        query = query.where(AuditLog.created_at >= since)
    rows = session.execute(query.order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        AuditOut(
            id=log.id,
            actor_id=log.actor_id,
            actor_name=name,
            actor_role=log.actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before=log.before,
            after=log.after,
            reason=log.reason,
            created_at=log.created_at,
        )
        for log, name in rows
    ]


class RunDetail(BaseModel):
    id: uuid.UUID
    pipeline: str
    status: str
    origin: str
    started_at: datetime
    finished_at: datetime | None
    code_version: str
    inputs: list[dict[str, Any]]
    row_counts: dict[str, int]
    checks: list[dict[str, Any]]


@router.get("/pipeline-runs", response_model=list[RunDetail])
def pipeline_runs(session: SessionDep, principal: Admin) -> list[RunDetail]:
    runs = session.scalars(select(PipelineRun).order_by(PipelineRun.started_at.desc())).all()
    return [RunDetail.model_validate(r, from_attributes=True) for r in runs]
