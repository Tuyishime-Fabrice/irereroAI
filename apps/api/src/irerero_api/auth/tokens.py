import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from irerero_api.auth.principal import Principal
from irerero_api.config import Settings
from irerero_contract.enums import Role, ScopeLevel
from irerero_contract.tables import RefreshToken, UserAccount

ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    pass


def _encode(claims: dict[str, Any], settings: Settings) -> str:
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def _decode(token: str, kind: str, settings: Settings) -> dict[str, Any]:
    try:
        claims: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as error:
        raise InvalidTokenError(str(error)) from error
    if claims.get("typ") != kind:
        raise InvalidTokenError("wrong token type")
    return claims


def issue_tokens(session: Session, user: UserAccount, settings: Settings) -> tuple[str, str]:
    now = datetime.now(UTC)
    access = _encode(
        {
            "typ": "access",
            "sub": str(user.id),
            "role": user.role.value,
            "scope_level": user.scope_level.value,
            "scope_code": user.scope_code,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        settings,
    )
    refresh_id = uuid.uuid4()
    expires = now + timedelta(days=settings.refresh_token_days)
    session.add(RefreshToken(id=refresh_id, user_id=user.id, expires_at=expires))
    refresh = _encode(
        {"typ": "refresh", "sub": str(user.id), "jti": str(refresh_id), "exp": expires}, settings
    )
    return access, refresh


def principal_from_access(token: str, settings: Settings) -> Principal:
    claims = _decode(token, "access", settings)
    return Principal(
        id=uuid.UUID(claims["sub"]),
        role=Role(claims["role"]),
        scope_level=ScopeLevel(claims["scope_level"]),
        scope_code=claims.get("scope_code"),
    )


def rotate_refresh(session: Session, token: str, settings: Settings) -> UserAccount:
    """Revoke the presented refresh token and return its user, so new tokens can be issued."""
    claims = _decode(token, "refresh", settings)
    stored = session.get(RefreshToken, uuid.UUID(claims["jti"]))
    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise InvalidTokenError("refresh token is not valid")
    stored.revoked_at = now
    user = session.get(UserAccount, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("account is not active")
    return user


def revoke_all(session: Session, user_id: uuid.UUID) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def active_user(session: Session, user_id: uuid.UUID) -> UserAccount | None:
    return session.scalars(
        select(UserAccount).where(UserAccount.id == user_id, UserAccount.is_active)
    ).first()
