"""Demo mode only: demo accounts, the admin's current code, and one-tap sign-in for the tour."""

from datetime import date
from typing import Annotated

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.demo import DEMO_PASSWORD, DEMO_TOTP_SECRET
from irerero_api.routes.auth import tokens_for
from irerero_api.schemas.auth import TokenResponse
from irerero_contract.enums import Role
from irerero_contract.tables import UserAccount

router = APIRouter(prefix="/demo", tags=["demo"])
SessionDep = Annotated[Session, Depends(get_session)]


class DemoAccountOut(BaseModel):
    role: Role
    display_name: str
    email: str | None
    phone: str | None
    centre_code: str | None


class DemoConfig(BaseModel):
    current_week: date
    password: str
    admin_totp_code: str
    accounts: list[DemoAccountOut]


def _require_demo() -> None:
    if not get_settings().demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available")


def _first_of_role(session: Session, role: Role) -> UserAccount | None:
    return session.scalars(
        select(UserAccount)
        .where(UserAccount.role == role, UserAccount.is_active)
        .order_by(UserAccount.created_at, UserAccount.id)
    ).first()


@router.get("/config", response_model=DemoConfig, dependencies=[Depends(_require_demo)])
def demo_config(session: SessionDep) -> DemoConfig:
    accounts = []
    for role in Role:
        user = _first_of_role(session, role)
        if user is not None:
            accounts.append(
                DemoAccountOut(
                    role=role,
                    display_name=user.display_name,
                    email=user.email,
                    phone=user.phone,
                    centre_code=user.scope_code if role is Role.CAREGIVER else None,
                )
            )
    return DemoConfig(
        current_week=get_settings().demo_current_week,
        password=DEMO_PASSWORD,
        admin_totp_code=pyotp.TOTP(DEMO_TOTP_SECRET).now(),
        accounts=accounts,
    )


@router.post("/login/{role}", response_model=TokenResponse, dependencies=[Depends(_require_demo)])
def demo_login(role: Role, session: SessionDep) -> TokenResponse:
    user = _first_of_role(session, role)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No demo account for that role")
    return tokens_for(session, user)
