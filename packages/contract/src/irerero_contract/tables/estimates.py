import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import DRIVERS_INFO, Base, Provenance, count, new_uuid


def _ordered(prefix: str) -> CheckConstraint:
    return CheckConstraint(
        f"{prefix}_low <= {prefix}_estimate AND {prefix}_estimate <= {prefix}_high",
        name=f"{prefix}_range_ordered",
    )


def _share(comment: str) -> Mapped[float]:
    return mapped_column(Float, comment=comment, info={"minimum": 0, "maximum": 1})


class NeedEstimate(Provenance, Base):
    """Estimated need per area with an interval for every value. Produced by NeedEstimator."""

    __tablename__ = "need_estimate"
    __table_args__ = (
        _ordered("children_0_2"),
        _ordered("children_3_6"),
        _ordered("stunting_risk"),
        _ordered("mothers_barrier_share"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Row id")
    area_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"),
        index=True,
        comment="Sector for district deep dives, district for the national map",
    )
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_version.id"), comment="Model that produced the estimate"
    )
    children_0_2_estimate: Mapped[int] = count("Children aged 0 to 2, point estimate")
    children_0_2_low: Mapped[int] = count("Children aged 0 to 2, lower bound")
    children_0_2_high: Mapped[int] = count("Children aged 0 to 2, upper bound")
    children_3_6_estimate: Mapped[int] = count("Children aged 3 to 6, point estimate")
    children_3_6_low: Mapped[int] = count("Children aged 3 to 6, lower bound")
    children_3_6_high: Mapped[int] = count("Children aged 3 to 6, upper bound")
    stunting_risk_estimate: Mapped[float] = _share("Share of under-5s at risk of stunting")
    stunting_risk_low: Mapped[float] = _share("Stunting risk, lower bound")
    stunting_risk_high: Mapped[float] = _share("Stunting risk, upper bound")
    mothers_barrier_share_estimate: Mapped[float] = _share(
        "Share of mothers of under-3s who report childcare as a barrier to work"
    )
    mothers_barrier_share_low: Mapped[float] = _share("Mothers' childcare barrier, lower bound")
    mothers_barrier_share_high: Mapped[float] = _share("Mothers' childcare barrier, upper bound")
    top_drivers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Up to five drivers: [{feature, label_en, label_rw, contribution}]",
        info=DRIVERS_INFO,
    )


class CoverageSnapshot(Provenance, Base):
    """Weekly coverage per sector. Produced by CoverageModel from centres and need."""

    __tablename__ = "coverage_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Row id")
    area_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector"
    )
    week_start: Mapped[date] = mapped_column(Date, index=True, comment="Monday of the week")
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_version.id"), comment="Coverage model that produced the row"
    )
    children_covered: Mapped[int] = count("Children 0 to 6 with a place within the catchment")
    children_uncovered: Mapped[int] = count("Children 0 to 6 without a reachable place")
    overcrowded_centres: Mapped[int] = count("Centres with attendance above capacity")
    catchment_minutes: Mapped[int] = mapped_column(
        SmallInteger, comment="Walking time used for the catchment", info={"minimum": 1}
    )


class AreaIndicator(Provenance, Base):
    """Source indicators aligned to an area. Phase 2 adapters write here; models read here."""

    __tablename__ = "area_indicator"
    __table_args__ = (
        CheckConstraint(
            "(low IS NULL AND high IS NULL) OR (low <= value AND value <= high)",
            name="range_ordered",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Row id")
    area_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Area the value describes"
    )
    indicator: Mapped[str] = mapped_column(
        String(64), index=True, comment="Indicator code from docs/DATA_CONTRACT.md#indicators"
    )
    value: Mapped[float] = mapped_column(Float, comment="Value in the indicator's unit")
    low: Mapped[float | None] = mapped_column(
        Float, comment="Lower bound when the source gives one"
    )
    high: Mapped[float | None] = mapped_column(
        Float, comment="Upper bound when the source gives one"
    )
    unit: Mapped[str] = mapped_column(String(32), comment="count | share | minutes | rwf")
    sample_size: Mapped[int | None] = mapped_column(
        Integer, comment="Survey respondents behind the value, when survey-based"
    )
    reference_date: Mapped[date | None] = mapped_column(
        Date, comment="Exact date when finer than reference_year"
    )
