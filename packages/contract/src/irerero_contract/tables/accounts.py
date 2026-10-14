import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type, new_uuid
from irerero_contract.enums import Role


class UserAccount(Base):
    """District planners. Role and district are copied into every access token."""

    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    role: Mapped[Role] = mapped_column(enum_type(Role), comment="Role")
    district_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), comment="District the planner plans for"
    )
    display_name: Mapped[str] = mapped_column(String(120), comment="Name shown in the app")
    email: Mapped[str] = mapped_column(String(254), unique=True, comment="Login")
    password_hash: Mapped[str] = mapped_column(String(255), comment="Argon2id hash")
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
