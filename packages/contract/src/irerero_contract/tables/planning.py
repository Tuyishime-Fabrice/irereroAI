import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import (
    DRIVERS_INFO,
    Base,
    Provenance,
    count,
    created_at_column,
    enum_type,
    new_uuid,
    point,
)
from irerero_contract.enums import (
    Action,
    CandidateKind,
    CostBand,
    Origin,
    RecommendationStatus,
    RejectionReason,
    Verdict,
)


class UnitCost(Provenance, Base):
    """Cost of one action by cost band, used by the optimizer and the what-if simulator."""

    __tablename__ = "unit_cost"
    __table_args__ = (
        CheckConstraint("cost_low_rwf <= cost_rwf AND cost_rwf <= cost_high_rwf", name="ordered"),
    )

    action: Mapped[Action] = mapped_column(
        enum_type(Action), primary_key=True, comment="build | upgrade | support"
    )
    band: Mapped[CostBand] = mapped_column(
        enum_type(CostBand), primary_key=True, comment="low | medium | high"
    )
    cost_rwf: Mapped[int] = mapped_column(BigInteger, comment="Expected cost in RWF")
    cost_low_rwf: Mapped[int] = mapped_column(BigInteger, comment="Lower bound in RWF")
    cost_high_rwf: Mapped[int] = mapped_column(BigInteger, comment="Upper bound in RWF")
    places_added: Mapped[int] = count("New places the action creates")


class CandidateSite(Provenance, Base):
    """A place where an action could happen: a village or school to build at, or a centre."""

    __tablename__ = "candidate_site"
    __table_args__ = (
        CheckConstraint(
            "(kind IN ('centre_upgrade', 'centre_support')) = (centre_code IS NOT NULL)",
            name="centre_kinds_have_centre",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="Site code")
    kind: Mapped[CandidateKind] = mapped_column(
        enum_type(CandidateKind), comment="village | school | centre_upgrade | centre_support"
    )
    name: Mapped[str] = mapped_column(String(160), comment="Village, school or centre name")
    sector_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector of the site"
    )
    centre_code: Mapped[str | None] = mapped_column(
        ForeignKey("centre.code"), comment="Existing centre for upgrade and support sites"
    )
    location: Mapped[Any] = mapped_column(point(), comment="Site location, EPSG:4326")
    unit_cost_band: Mapped[CostBand] = mapped_column(
        enum_type(CostBand), comment="Cost band looked up in unit_cost"
    )


class Scenario(Base):
    """A planning run: budget, policy weights and constraints chosen by a person."""

    __tablename__ = "scenario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    district_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="District being planned"
    )
    name: Mapped[str] = mapped_column(String(120), comment="Label shown in comparisons")
    budget_rwf: Mapped[int] = mapped_column(
        BigInteger, comment="Budget in RWF", info={"minimum": 0}
    )
    weight_stunting: Mapped[float] = mapped_column(
        Float, comment="Policy weight on high stunting risk", info={"minimum": 0, "maximum": 1}
    )
    weight_readiness: Mapped[float] = mapped_column(
        Float,
        comment="Policy weight on uncovered 3 to 6 year olds",
        info={"minimum": 0, "maximum": 1},
    )
    weight_jobs: Mapped[float] = mapped_column(
        Float,
        comment="Policy weight on mothers' childcare barrier",
        info={"minimum": 0, "maximum": 1},
    )
    constraints: Mapped[dict[str, Any]] = mapped_column(
        JSONB, comment="Extra constraints: {excluded_site_ids, max_actions_per_sector}"
    )
    is_baseline: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="True for the largest-population-first comparison run"
    )
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_version.id"), comment="Optimizer version"
    )
    origin: Mapped[Origin] = mapped_column(
        enum_type(Origin), comment="simulated when any input record is simulated"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id"), comment="Planner who ran it"
    )
    created_at: Mapped[datetime] = created_at_column()


class Recommendation(Base):
    """One ranked suggestion in a scenario. Never acted on until a person approves it."""

    __tablename__ = "recommendation"
    __table_args__ = (
        CheckConstraint(
            "reached_low <= children_reached AND children_reached <= reached_high",
            name="reached_range_ordered",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenario.id", ondelete="CASCADE"), index=True, comment="Scenario"
    )
    rank: Mapped[int] = count("1 is the strongest suggestion")
    action: Mapped[Action] = mapped_column(enum_type(Action), comment="build | upgrade | support")
    site_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_site.id"), comment="Target site or centre"
    )
    children_reached: Mapped[int] = count("Uncovered children 0 to 6 who gain a reachable place")
    reached_low: Mapped[int] = count("Children reached, lower bound")
    reached_high: Mapped[int] = count("Children reached, upper bound")
    high_risk_children_reached: Mapped[int] = count("Children reached in high stunting-risk areas")
    mothers_under3_reached: Mapped[int] = count(
        "Mothers of under-3s in the catchment who report childcare as a barrier"
    )
    cost_rwf: Mapped[int] = mapped_column(BigInteger, comment="Expected cost in RWF")
    score: Mapped[float] = mapped_column(Float, comment="Weighted benefit per RWF used to rank")
    drivers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Top reasons: [{feature, label_en, label_rw, contribution}]",
        info=DRIVERS_INFO,
    )
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, comment="Inputs used: [{table, source, reference_year, origin}]"
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        enum_type(RecommendationStatus),
        default=RecommendationStatus.PROPOSED,
        comment="proposed | approved | edited | rejected",
    )


class Decision(Base):
    """A person's verdict on a recommendation. Rejection reasons feed the next run."""

    __tablename__ = "decision"
    __table_args__ = (
        CheckConstraint("verdict <> 'reject' OR reason_code IS NOT NULL", name="reject_has_reason"),
        CheckConstraint(
            "reason_code <> 'other' OR length(trim(reason_text)) > 0", name="other_has_text"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation.id", ondelete="CASCADE"), index=True, comment="Recommendation"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id"), comment="Person who decided"
    )
    verdict: Mapped[Verdict] = mapped_column(enum_type(Verdict), comment="approve | edit | reject")
    reason_code: Mapped[RejectionReason | None] = mapped_column(
        enum_type(RejectionReason),
        comment="no_land | already_funded | access_problem | community_objection | other",
    )
    reason_text: Mapped[str | None] = mapped_column(Text, comment="Free-text explanation")
    edits: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, comment="Changed fields for an edit: {field: {from, to}}"
    )
    created_at: Mapped[datetime] = created_at_column()
