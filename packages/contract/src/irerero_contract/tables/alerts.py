import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type, new_uuid
from irerero_contract.enums import AlertKind, AlertSeverity, AlertStatus, Origin


class Alert(Base):
    """An early-warning signal for one centre and week, with its reason in plain words."""

    __tablename__ = "alert"
    __table_args__ = (UniqueConstraint("centre_code", "week_start", "kind", name="one_per_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    centre_code: Mapped[str] = mapped_column(
        ForeignKey("centre.code"), index=True, comment="Centre concerned"
    )
    week_start: Mapped[date] = mapped_column(Date, index=True, comment="Week the signal fired")
    kind: Mapped[AlertKind] = mapped_column(
        enum_type(AlertKind),
        comment="attendance_drop | missing_report | overcrowding | wash | closure_risk",
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        enum_type(AlertSeverity), comment="info | warning | critical"
    )
    reason_en: Mapped[str] = mapped_column(Text, comment="Reason in English")
    reason_rw: Mapped[str] = mapped_column(Text, comment="Reason in Kinyarwanda")
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, comment="Numbers the rule used, e.g. {attendance, baseline_mean, z_score}"
    )
    rule: Mapped[str] = mapped_column(String(48), comment="Rule id inside the early-warning model")
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_version.id"), comment="Early-warning version"
    )
    origin: Mapped[Origin] = mapped_column(
        enum_type(Origin), comment="Origin of the reports the alert was computed from"
    )
    status: Mapped[AlertStatus] = mapped_column(
        enum_type(AlertStatus), default=AlertStatus.OPEN, comment="open | acknowledged | resolved"
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id"), comment="Officer following up"
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, comment="What was done")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last status change",
    )
