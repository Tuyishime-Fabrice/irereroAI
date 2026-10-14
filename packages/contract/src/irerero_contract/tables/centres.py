from datetime import date
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, Provenance, count, enum_type, point
from irerero_contract.enums import CentreStatus, CentreType, FeeBand


class Centre(Provenance, Base):
    """An ECD centre. Mirrors the NCDA ECD Mapping System record so a connector can sync it."""

    __tablename__ = "centre"
    __table_args__ = (
        CheckConstraint("serves_0_2 OR serves_3_6", name="serves_an_age_band"),
        CheckConstraint("enrolment >= 0", name="enrolment_min"),
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
        Boolean, default=False, comment="Marked verified in the NCDA ECD Mapping System"
    )
    water_available: Mapped[bool] = mapped_column(
        Boolean, comment="Has safe drinking water and handwashing on site"
    )
    enrolment: Mapped[int] = count("Children enrolled, from the latest attendance feed record")
    enrolment_as_of: Mapped[date] = mapped_column(
        Date, comment="Date of the attendance feed record the enrolment comes from"
    )
    ncda_ref: Mapped[str | None] = mapped_column(
        String(64), unique=True, comment="Record identifier in the NCDA ECD Mapping System"
    )
