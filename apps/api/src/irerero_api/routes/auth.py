import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import pyotp
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
from irerero_api.phone import normalise_phone
from irerero_api.schemas.auth import (
    CaregiverLogin,
    Me,
    OtpRequest,
    OtpRequested,
    OtpVerify,
    RefreshRequest,
    StaffLogin,
    TokenResponse,
)
from irerero_contract.enums import Role, ScopeLevel
from irerero_contract.passwords import hash_secret, verify_secret
from irerero_contract.tables import AdminUnit, Centre, OtpChallenge, UserAccount

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDep = Annotated[Session, Depends(get_session)]
WRONG = HTTPException(status.HTTP_401_UNAUTHORIZED, "Those details do not match an account")


def me(session: Session, user: UserAccount) -> Me:
    scope_name = None
    if user.scope_code:
        unit = session.get(AdminUnit, user.scope_code)
        centre = session.get(Centre, user.scope_code) if unit is None else None
        scope_name = unit.name if unit else (centre.name if centre else None)
    return Me(
        id=user.id,
        role=user.role,
        scope_level=user.scope_level,
        scope_code=user.scope_code,
        scope_name=scope_name,
        display_name=user.display_name,
    )


def tokens_for(session: Session, user: UserAccount) -> TokenResponse:
    access, refresh = issue_tokens(session, user, get_settings())
    return TokenResponse(access_token=access, refresh_token=refresh, user=me(session, user))


@router.post("/login", response_model=TokenResponse)
def staff_login(body: StaffLogin, session: SessionDep) -> TokenResponse:
    user = session.scalars(
        select(UserAccount).where(UserAccount.email == body.email.strip().lower())
    ).first()
    if user is None or not user.is_active or not user.password_hash:
        raise WRONG
    if not verify_secret(user.password_hash, body.password):
        raise WRONG
    if user.role is Role.ADMIN:
        if not user.totp_secret:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Two-factor setup required")
        if not body.totp_code or not pyotp.TOTP(user.totp_secret).verify(
            body.totp_code, valid_window=1
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Enter the 6-digit code")
    return tokens_for(session, user)


@router.post("/caregiver", response_model=TokenResponse)
def caregiver_login(body: CaregiverLogin, session: SessionDep) -> TokenResponse:
    phone = normalise_phone(body.phone)
    user = session.scalars(
        select(UserAccount).where(
            UserAccount.phone == phone,
            UserAccount.role == Role.CAREGIVER,
            UserAccount.scope_code == body.centre_code.strip().upper(),
            UserAccount.is_active,
        )
    ).first()
    if user is None:
        raise WRONG
    return tokens_for(session, user)


@router.post("/otp/request", response_model=OtpRequested)
def request_code(body: OtpRequest, session: SessionDep) -> OtpRequested:
    settings = get_settings()
    phone = normalise_phone(body.phone)
    if phone is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a Rwandan mobile number")
    code = f"{secrets.randbelow(1_000_000):06d}"
    session.add(
        OtpChallenge(
            phone=phone,
            code_hash=hash_secret(code),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.otp_minutes),
        )
    )
    # Phase 1 has no SMS gateway: the code is only ever returned in demo mode.
    return OtpRequested(
        expires_in_seconds=settings.otp_minutes * 60,
        demo_code=code if settings.demo_mode else None,
    )


@router.post("/otp/verify", response_model=TokenResponse)
def verify_code(body: OtpVerify, session: SessionDep) -> TokenResponse:
    settings = get_settings()
    phone = normalise_phone(body.phone)
    challenge = session.scalars(
        select(OtpChallenge)
        .where(
            OtpChallenge.phone == phone,
            OtpChallenge.consumed_at.is_(None),
            OtpChallenge.expires_at > datetime.now(UTC),
        )
        .order_by(OtpChallenge.created_at.desc())
    ).first()
    if challenge is None or challenge.attempts >= settings.otp_max_attempts:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Request a new code")
    if not verify_secret(challenge.code_hash, body.code.strip()):
        challenge.attempts += 1
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That code is not right")
    challenge.consumed_at = datetime.now(UTC)
    user = session.scalars(select(UserAccount).where(UserAccount.phone == phone)).first()
    if user is None:
        user = UserAccount(
            role=Role.PARENT, scope_level=ScopeLevel.NONE, display_name="Parent", phone=phone
        )
        session.add(user)
        session.flush()
    elif user.role is not Role.PARENT or not user.is_active:
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
