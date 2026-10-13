import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, Provenance, count, days, enum_type, new_uuid
from irerero_contract.enums import MainProblem, QualityFlag, ReportChannel

ENROLLED_TOTAL = "enrolled_0_2_female + enrolled_0_2_male + enrolled_3_6_female + enrolled_3_6_male"


class WeeklyReport(Provenance, Base):
    """The weekly centre report: about ten counts, no child-level data."""

    __tablename__ = "weekly_report"
    __table_args__ = (
        UniqueConstraint("centre_code", "week_start", name="one_per_week"),
        CheckConstraint(f"avg_daily_attendance <= {ENROLLED_TOTAL}", name="attendance_le_enrolled"),
        CheckConstraint("extract(isodow from week_start) = 1", name="week_starts_monday"),
        CheckConstraint("days_meal_served <= days_open", name="meals_le_days_open"),
        CheckConstraint(
            f"children_with_disability <= {ENROLLED_TOTAL}", name="disability_le_enrolled"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Report id")
    centre_code: Mapped[str] = mapped_column(
        ForeignKey("centre.code"), index=True, comment="Reporting centre"
    )
    week_start: Mapped[date] = mapped_column(
        Date, index=True, comment="Monday of the reported week"
    )
    enrolled_0_2_female: Mapped[int] = count("Girls aged 0 to 2 enrolled")
    enrolled_0_2_male: Mapped[int] = count("Boys aged 0 to 2 enrolled")
    enrolled_3_6_female: Mapped[int] = count("Girls aged 3 to 6 enrolled")
    enrolled_3_6_male: Mapped[int] = count("Boys aged 3 to 6 enrolled")
    avg_daily_attendance: Mapped[int] = count("Average number of children present per open day")
    waiting_list: Mapped[int] = count("Children waiting for a place")
    caregivers_present: Mapped[int] = count("Caregivers present on a typical day")
    days_open: Mapped[int] = days("Days the centre opened this week, 0 to 6")
    days_meal_served: Mapped[int] = days("Days a meal was served, 0 to 6")
    wash_available: Mapped[bool] = mapped_column(
        Boolean, comment="Water and handwashing were available all week"
    )
    referrals_growth_monitoring: Mapped[int] = count(
        "Children referred to growth monitoring this week"
    )
    children_with_disability: Mapped[int] = count("Enrolled children with a known disability")
    main_problem: Mapped[MainProblem] = mapped_column(
        enum_type(MainProblem),
        comment="none | no_food | no_water | caregiver_absent | building_damage | weather | other",
    )
    channel: Mapped[ReportChannel] = mapped_column(
        enum_type(ReportChannel), comment="web | offline | sms | assisted"
    )
    quality_flags: Mapped[list[QualityFlag]] = mapped_column(
        ARRAY(String(32)),
        default=list,
        comment="Validation flags. Flagged reports are kept and shown, never silently accepted",
        info={"items_enum": QualityFlag},
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id"), comment="Account that submitted or entered the report"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="When the server received it"
    )
