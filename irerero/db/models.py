"""Every table. Analysis tables are rebuilt by `make data`; app tables (plans, LEARN progress,
the audit log) are kept across rebuilds so decisions and training survive."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---- Analysis tables: rebuilt from data files by `make data` -------------------------------


class GeoUnit(Base):
    __tablename__ = "geo_unit"

    geo_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16))  # country | province | district | sector
    name: Mapped[str] = mapped_column(String(120))
    parent_id: Mapped[str | None] = mapped_column(String(64), index=True)
    nisr_code: Mapped[str | None] = mapped_column(String(16))
    province: Mapped[str | None] = mapped_column(String(64))
    district: Mapped[str | None] = mapped_column(String(64))
    area_km2: Mapped[float | None] = mapped_column(Float)


class Source(Base):
    __tablename__ = "source"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(160))
    reference_period: Mapped[str] = mapped_column(String(32))
    url: Mapped[str | None] = mapped_column(String(300))
    licence: Mapped[str] = mapped_column(String(160))
    loaded: Mapped[bool] = mapped_column(Boolean)
    """True when the real file was loaded; False when demo data stood in."""
    notes: Mapped[str | None] = mapped_column(Text)


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (UniqueConstraint("geo_id", "indicator_id", "reference_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_unit.geo_id"), index=True)
    indicator_id: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)
    reference_period: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"))
    source_page: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    qa_flag: Mapped[str | None] = mapped_column(String(120))


class Estimate2026(Base):
    __tablename__ = "estimate_2026"

    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_unit.geo_id"), primary_key=True)
    children_3_5: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    attendance_rate_2022: Mapped[float] = mapped_column(Float)
    attendance_rate: Mapped[float] = mapped_column(Float)
    attending: Mapped[float] = mapped_column(Float)
    far_share: Mapped[float | None] = mapped_column(Float)
    """Share of young children more than 1 km from a school with pre-primary."""
    distance_method: Mapped[str | None] = mapped_column(String(64))
    children_spread: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24))
    method: Mapped[str] = mapped_column(Text)


class ModelRun(Base):
    __tablename__ = "model_run"

    model_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    chosen: Mapped[bool] = mapped_column(Boolean)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)


class ModelOutput(Base):
    __tablename__ = "model_output"

    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_unit.geo_id"), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(48))
    observed: Mapped[float] = mapped_column(Float)
    expected: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    drivers: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24))


class Diagnosis(Base):
    __tablename__ = "diagnosis"

    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_unit.geo_id"), primary_key=True)
    access: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[float | None] = mapped_column(Float)
    wellbeing: Mapped[float | None] = mapped_column(Float)
    home: Mapped[float | None] = mapped_column(Float)
    poverty: Mapped[float | None] = mapped_column(Float)
    bottleneck: Mapped[str] = mapped_column(String(16))
    intervention: Mapped[str] = mapped_column(Text)
    reasons: Mapped[list[str]] = mapped_column(JSON)
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    """Raw indicator values behind each factor, and the level they are measured at."""
    status: Mapped[str] = mapped_column(String(24))


class Forecast(Base):
    __tablename__ = "forecast"

    geo_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    year: Mapped[str] = mapped_column(String(8), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)  # observed|projected|backtest
    value: Mapped[float] = mapped_column(Float)
    """Gross pre-primary enrolment rate."""
    children: Mapped[float | None] = mapped_column(Float)
    """Children aged 3 to 5 that year (NISR projection x census 3-5 share)."""
    pupils: Mapped[float | None] = mapped_column(Float)
    """MINEDUC pre-primary pupils (observed years only)."""
    low: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))


class SupplyExtract(Base):
    """NCDA ECD Mapping System extract. Simulated for Muhanga until NCDA shares data."""

    __tablename__ = "supply_extract"

    centre_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    centre_type: Mapped[str] = mapped_column(String(24))
    geo_id: Mapped[str] = mapped_column(ForeignKey("geo_unit.geo_id"), index=True)
    lon: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)
    enrolled_3_5: Mapped[int] = mapped_column(Integer)
    caregivers: Mapped[int] = mapped_column(Integer)
    as_of: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(24))


class Course(Base):
    __tablename__ = "course"

    course_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(160))
    title_rw: Mapped[str] = mapped_column(String(160))
    required_on_joining: Mapped[bool] = mapped_column(Boolean)
    trigger: Mapped[str | None] = mapped_column(String(48))
    source: Mapped[str] = mapped_column(Text)


class Lesson(Base):
    __tablename__ = "lesson"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("course.course_id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160))
    body_md: Mapped[str] = mapped_column(Text)


class QuizItem(Base):
    __tablename__ = "quiz_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("course.course_id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    answer: Mapped[int] = mapped_column(Integer)


# ---- App tables: kept across data rebuilds -------------------------------------------------


class AppUser(Base):
    """Demo users only: invented names, no personal data."""

    __tablename__ = "app_user"

    user_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    role: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(120))
    district_id: Mapped[str | None] = mapped_column(String(64))
    sector_id: Mapped[str | None] = mapped_column(String(64))
    centre_id: Mapped[str | None] = mapped_column(String(32))


class Plan(Base):
    __tablename__ = "plan"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target: Mapped[float] = mapped_column(Float)
    preset: Mapped[str] = mapped_column(String(48))
    weights: Mapped[list[float]] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class PlanItem(Base):
    __tablename__ = "plan_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.plan_id"), index=True)
    geo_id: Mapped[str] = mapped_column(String(64))
    rank: Mapped[int] = mapped_column(Integer)
    places: Mapped[int] = mapped_column(Integer)
    rooms: Mapped[int] = mapped_column(Integer)
    caregivers_low: Mapped[int] = mapped_column(Integer)
    caregivers_high: Mapped[int] = mapped_column(Integer)
    bottleneck: Mapped[str] = mapped_column(String(16))
    intervention: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(16), default="pending")
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="planned")
    decided_by: Mapped[str | None] = mapped_column(String(48))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)


class CentreCheckin(Base):
    __tablename__ = "centre_checkin"
    __table_args__ = (UniqueConstraint("centre_id", "month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    enrolled: Mapped[int] = mapped_column(Integer)
    attendance_avg: Mapped[float] = mapped_column(Float)
    caregivers_present: Mapped[int] = mapped_column(Integer)
    meal_days_avg: Mapped[float] = mapped_column(Float)
    water_available: Mapped[bool] = mapped_column(Boolean)
    main_challenge: Mapped[str] = mapped_column(String(24))
    submitted_by: Mapped[str] = mapped_column(String(48))
    submitted_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(24))


class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = (UniqueConstraint("caregiver_id", "course_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caregiver_id: Mapped[str] = mapped_column(String(48), index=True)
    # no foreign key: course content is rebuilt with the analysis tables, progress is kept
    course_id: Mapped[str] = mapped_column(String(32))
    trigger: Mapped[str] = mapped_column(String(64))
    """joining | checkin:no_water | checkin:few_meals | sector:WASH | sector:WELLBEING"""
    required_by: Mapped[str | None] = mapped_column(String(24))
    """None while only recommended; 'joining' or 'officer' once required."""
    confirmed_by: Mapped[str | None] = mapped_column(String(48))
    due_date: Mapped[date | None] = mapped_column(Date)
    lessons_done: Mapped[list[int]] = mapped_column(JSON, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    user_id: Mapped[str] = mapped_column(String(48))
    role: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(48))
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)


ANALYSIS_TABLES = (
    Observation,
    Estimate2026,
    ModelOutput,
    ModelRun,
    Diagnosis,
    Forecast,
    SupplyExtract,
    QuizItem,
    Lesson,
    Course,
    Source,
    GeoUnit,
)
