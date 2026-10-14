from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.auth.deps import current_principal
from irerero_api.auth.principal import Principal
from irerero_api.auth.tokens import (
    InvalidTokenError,
    active_user,
    issue_tokens,
    revoke_all,
    rotate_refresh,
)
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.auth import Login, Me, RefreshRequest, TokenResponse
from irerero_contract.passwords import verify_secret
from irerero_contract.tables import AdminUnit, UserAccount

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDep = Annotated[Session, Depends(get_session)]
WRONG = HTTPException(status.HTTP_401_UNAUTHORIZED, "Those details do not match an account")


def me(session: Session, user: UserAccount) -> Me:
    district = session.get(AdminUnit, user.district_code)
    return Me(
        id=user.id,
        role=user.role,
        district_code=user.district_code,
        district_name=district.name if district else user.district_code,
        display_name=user.display_name,
    )


def tokens_for(session: Session, user: UserAccount) -> TokenResponse:
    access, refresh = issue_tokens(session, user, get_settings())
    return TokenResponse(access_token=access, refresh_token=refresh, user=me(session, user))


@router.post("/login", response_model=TokenResponse)
def login(body: Login, session: SessionDep) -> TokenResponse:
    user = session.scalars(
        select(UserAccount).where(UserAccount.email == body.email.strip().lower())
    ).first()
    if user is None or not user.is_active or not verify_secret(user.password_hash, body.password):
        raise WRONG
    return tokens_for(session, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, session: SessionDep) -> TokenResponse:
    try:
        user = rotate_refresh(session, body.refresh_token, get_settings())
    except InvalidTokenError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again") from error
    return tokens_for(session, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: SessionDep, principal: Annotated[Principal, Depends(current_principal)]
) -> None:
    revoke_all(session, principal.id)


@router.get("/me", response_model=Me)
def whoami(session: SessionDep, principal: Annotated[Principal, Depends(current_principal)]) -> Me:
    user = active_user(session, principal.id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again")
    return me(session, user)
