import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type
from irerero_contract.enums import Role


class AuditLog(Base):
    """Append-only record of every human decision. A trigger rejects UPDATE and DELETE."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Id")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id"), index=True, comment="Account that acted"
    )
    actor_role: Mapped[Role] = mapped_column(enum_type(Role), comment="Role at the time")
    action: Mapped[str] = mapped_column(
        String(48), index=True, comment="e.g. recommendation.reject, centre.verify, alert.resolve"
    )
    entity_type: Mapped[str] = mapped_column(String(48), comment="Table of the changed row")
    entity_id: Mapped[str] = mapped_column(String(64), index=True, comment="Key of the changed row")
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="Values before")
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, comment="Values after")
    reason: Mapped[str | None] = mapped_column(Text, comment="Reason given by the person")
    created_at: Mapped[datetime] = created_at_column()
