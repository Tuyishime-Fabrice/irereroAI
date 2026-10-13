import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, Provenance, count, enum_type, point
from irerero_contract.enums import CentreStatus, CentreType, FeeBand


class Centre(Provenance, Base):
    """An ECD centre. Mirrors the NCDA ECD Mapping System record so a connector can sync it."""

    __tablename__ = "centre"
    __table_args__ = (
        CheckConstraint("reliability_score BETWEEN 0 AND 1", name="reliability_range"),
        CheckConstraint("serves_0_2 OR serves_3_6", name="serves_an_age_band"),
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True, comment="IrereroAI centre code")
    name: Mapped[str] = mapped_column(String(160), comment="Centre name as registered")
    type: Mapped[CentreType] = mapped_column(
        enum_type(CentreType),
        comment="home_based | community_based | school_based | centre_based",
    )
    status: Mapped[CentreStatus] = mapped_column(
        enum_type(CentreStatus), default=CentreStatus.ACTIVE, comment="active | closed"
    )
    sector_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector the centre is in"
    )
    location: Mapped[Any] = mapped_column(point(), comment="Centre location, EPSG:4326")
    capacity: Mapped[int] = count("Number of children the centre can take")
    serves_0_2: Mapped[bool] = mapped_column(Boolean, comment="Takes children aged 0 to 2")
    serves_3_6: Mapped[bool] = mapped_column(Boolean, comment="Takes children aged 3 to 6")
    opening_hours: Mapped[str] = mapped_column(
        String(64), comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00"'
    )
    fee_band: Mapped[FeeBand] = mapped_column(
        enum_type(FeeBand),
        comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000",
    )
    offers_meals: Mapped[bool] = mapped_column(Boolean, comment="Serves at least one meal a day")
    offers_growth_monitoring: Mapped[bool] = mapped_column(
        Boolean, comment="Hosts growth monitoring or refers to it"
    )
    disability_inclusive: Mapped[bool] = mapped_column(
        Boolean, comment="Has adapted space and trained caregivers for children with disabilities"
    )
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="A sector officer has checked the centre in person"
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the last verification happened"
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id"), nullable=True, comment="Officer who verified the centre"
    )
    reliability_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="0 to 1. Share of the last 12 weeks reported on time without quality flags",
        info={"minimum": 0, "maximum": 1},
    )
    ncda_ref: Mapped[str | None] = mapped_column(
        String(64), unique=True, comment="Record identifier in the NCDA ECD Mapping System"
    )
