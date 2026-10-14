"""Demo mode only: the demo planner's sign-in details and one-tap sign-in for the tour."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.demo import DEMO_PASSWORD
from irerero_api.routes.auth import tokens_for
from irerero_api.schemas.auth import TokenResponse
from irerero_contract.tables import UserAccount

router = APIRouter(prefix="/demo", tags=["demo"])
SessionDep = Annotated[Session, Depends(get_session)]


class DemoAccount(BaseModel):
    display_name: str
    email: str
    password: str


def _require_demo() -> None:
    if not get_settings().demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available")


def _demo_planner(session: Session) -> UserAccount:
    user = session.scalars(
        select(UserAccount)
        .where(UserAccount.is_active)
        .order_by(UserAccount.created_at, UserAccount.id)
    ).first()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No demo account; run the build")
    return user


@router.get("/account", response_model=DemoAccount, dependencies=[Depends(_require_demo)])
def demo_account(session: SessionDep) -> DemoAccount:
    user = _demo_planner(session)
    return DemoAccount(display_name=user.display_name, email=user.email, password=DEMO_PASSWORD)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_require_demo)])
def demo_login(session: SessionDep) -> TokenResponse:
    return tokens_for(session, _demo_planner(session))
