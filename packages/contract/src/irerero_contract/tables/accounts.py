import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type, new_uuid, point
from irerero_contract.enums import Role, ScopeLevel


class UserAccount(Base):
    """Staff, caregivers and parents. Role and scope are copied into every access token."""

    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="has_login"),
        CheckConstraint(
            "(scope_level IN ('none', 'national')) = (scope_code IS NULL)", name="scope"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    role: Mapped[Role] = mapped_column(enum_type(Role), comment="Role")
    scope_level: Mapped[ScopeLevel] = mapped_column(
        enum_type(ScopeLevel), comment="none | centre | sector | district | national"
    )
    scope_code: Mapped[str | None] = mapped_column(
        String(64), comment="Centre code or admin unit code the account may see"
    )
    display_name: Mapped[str] = mapped_column(String(120), comment="Name shown in the app")
    email: Mapped[str | None] = mapped_column(String(254), unique=True, comment="Staff login")
    phone: Mapped[str | None] = mapped_column(
        String(16), unique=True, comment="E.164 phone, parent and caregiver login"
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), comment="Argon2id hash")
    totp_secret: Mapped[str | None] = mapped_column(
        String(64), comment="TOTP secret. Required for admins"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Can sign in")
    created_at: Mapped[datetime] = created_at_column()


class RefreshToken(Base):
    """Issued refresh tokens, so they can be rotated and revoked."""

    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Token id")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), index=True, comment="Owner"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="Expiry")
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Set on rotation or sign-out"
    )
    created_at: Mapped[datetime] = created_at_column()


class OtpChallenge(Base):
    """One-time sign-in code for parents. Only the hash of the code is stored."""

    __tablename__ = "otp_challenge"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    phone: Mapped[str] = mapped_column(String(16), index=True, comment="E.164 phone")
    code_hash: Mapped[str] = mapped_column(String(255), comment="Argon2id hash of the code")
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, comment="Failed attempts")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="Expiry")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="Used")
    created_at: Mapped[datetime] = created_at_column()


class SavedSearch(Base):
    """A parent's saved search. Location is snapped to the 500 m grid, like demand signals."""

    __tablename__ = "saved_search"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), index=True, comment="Parent"
    )
    label: Mapped[str] = mapped_column(String(80), comment="Name the parent gave it")
    grid_cell: Mapped[str] = mapped_column(String(32), comment="500 m cell id")
    cell_centre: Mapped[Any] = mapped_column(point(), comment="Centre of the cell, EPSG:4326")
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, comment="{age_band, meals, max_fee_band, max_km}"
    )
    created_at: Mapped[datetime] = created_at_column()
