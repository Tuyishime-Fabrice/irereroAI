import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from irerero_api import audit
from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import forbidden, require_area
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.schemas.plan import (
    DecisionIn,
    DecisionLogRow,
    PlanningDefaults,
    ScenarioIn,
    ScenarioOut,
    ScenarioSummary,
    SimulateIn,
    SimulationOut,
    WeightsIn,
)
from irerero_api.services import plan as service
from irerero_contract.enums import Action, RecommendationStatus, Role, Verdict
from irerero_contract.tables import Decision, PlanningDefault, Recommendation, Scenario
from irerero_engine.optimizer import GreedyOptimizer, largest_population_first
from irerero_engine.types import SourceRef

router = APIRouter(tags=["plan"])
SessionDep = Annotated[Session, Depends(get_session)]
Planner = Annotated[Principal, Depends(require_roles(Role.DISTRICT_PLANNER, Role.ADMIN))]
Reader = Annotated[
    Principal,
    Depends(
        require_roles(Role.SECTOR_OFFICER, Role.DISTRICT_PLANNER, Role.NATIONAL_ANALYST, Role.ADMIN)
    ),
]
Decider = Annotated[
    Principal, Depends(require_roles(Role.SECTOR_OFFICER, Role.DISTRICT_PLANNER, Role.ADMIN))
]
Analyst = Annotated[Principal, Depends(require_roles(Role.NATIONAL_ANALYST, Role.ADMIN))]
EDITABLE = {"cost_rwf"}
FALLBACK_DEFAULTS = PlanningDefaults(
    area_code="RW", budget_rwf=120_000_000, weights=WeightsIn(stunting=0.4, readiness=0.4, jobs=0.2)
)


def _sources(out: ScenarioOut) -> list[SourceRef]:
    return [
        SourceRef(s.table, s.source, s.reference_year, s.origin.value)
        for rec in out.recommendations + out.rejected
        for s in rec.sources
    ]


def _envelope(session: Session, scenario: Scenario) -> Envelope[ScenarioOut]:
    out = service.scenario_out(session, get_settings(), scenario)
    return wrap(out, _sources(out))


def _scenario(session: Session, principal: Principal, scenario_id: uuid.UUID) -> Scenario:
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown scenario")
    require_area(session, principal, scenario.district_code)
    return scenario


@router.post(
    "/scenarios", response_model=Envelope[ScenarioOut], status_code=status.HTTP_201_CREATED
)
def run_scenario(
    body: ScenarioIn, session: SessionDep, principal: Planner
) -> Envelope[ScenarioOut]:
    require_area(session, principal, body.district_code)
    scenario = service.create(session, get_settings(), principal, body)
    audit.record(
        session,
        principal,
        "scenario.run",
        "scenario",
        str(scenario.id),
        after={"budget_rwf": body.budget_rwf, "weights": body.weights.model_dump()},
    )
    return _envelope(session, scenario)


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios(district: str, session: SessionDep, principal: Planner) -> list[ScenarioSummary]:
    require_area(session, principal, district)
    rows = session.execute(
        text(
            "SELECT s.*, u.display_name AS created_by_name, "
            "count(*) FILTER (WHERE r.status IN ('approved', 'edited')) AS approved, "
            "count(*) FILTER (WHERE r.status = 'rejected') AS rejected, "
            "count(*) FILTER (WHERE r.status = 'proposed') AS proposed "
            "FROM scenario s JOIN user_account u ON u.id = s.created_by "
            "LEFT JOIN recommendation r ON r.scenario_id = s.id "
            "WHERE s.district_code = :d AND NOT s.is_baseline "
            "GROUP BY s.id, u.display_name ORDER BY s.created_at DESC"
        ),
        {"d": district},
    ).all()
    return [
        ScenarioSummary(
            id=r.id,
            name=r.name,
            budget_rwf=r.budget_rwf,
            weights=WeightsIn(
                stunting=r.weight_stunting, readiness=r.weight_readiness, jobs=r.weight_jobs
            ),
            created_at=r.created_at,
            created_by_name=r.created_by_name,
            approved=r.approved,
            rejected=r.rejected,
            proposed=r.proposed,
        )
        for r in rows
    ]


@router.get("/scenarios/{scenario_id}", response_model=Envelope[ScenarioOut])
def get_scenario(
    scenario_id: uuid.UUID, session: SessionDep, principal: Planner
) -> Envelope[ScenarioOut]:
    return _envelope(session, _scenario(session, principal, scenario_id))


@router.post("/simulate", response_model=SimulationOut)
def simulate(body: SimulateIn, session: SessionDep, principal: Planner) -> SimulationOut:
    """What-if: outcomes of a budget and weights without saving anything."""
    require_area(session, principal, body.district_code)
    settings = get_settings()
    data = service.build_input(session, settings, body.district_code, body.budget_rwf, body.weights)
    model = service.coverage_model(settings)
    plan = GreedyOptimizer(model).plan(data)
    baseline = None
    if body.include_baseline:
        base = largest_population_first(model, data)
        baseline = service.outcomes_out(base.outcomes, [s.candidate for s in base.suggestions])
    return SimulationOut(
        outcomes=service.outcomes_out(plan.outcomes, [s.candidate for s in plan.suggestions]),
        baseline=baseline,
    )


@router.get("/local-suggestions", response_model=Envelope[ScenarioOut] | None)
def local_suggestions(
    sector: str, session: SessionDep, principal: Reader
) -> Envelope[ScenarioOut] | None:
    """The latest district plan, for a sector officer to review the suggestions in their sector."""
    chain = require_area(session, principal, sector)
    scenario = session.scalars(
        select(Scenario)
        .where(Scenario.district_code == chain.district, Scenario.is_baseline.is_(False))
        .order_by(Scenario.created_at.desc())
    ).first()
    if scenario is None:
        return None
    out = service.scenario_out(session, get_settings(), scenario)
    out.recommendations = [r for r in out.recommendations if r.sector_code == sector]
    out.rejected = [r for r in out.rejected if r.sector_code == sector]
    return wrap(out, _sources(out))


@router.post("/recommendations/{recommendation_id}/decision", response_model=Envelope[ScenarioOut])
def decide(
    recommendation_id: uuid.UUID, body: DecisionIn, session: SessionDep, principal: Decider
) -> Envelope[ScenarioOut]:
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown suggestion")
    scenario = session.get(Scenario, rec.scenario_id)
    assert scenario is not None
    site_sector = session.execute(
        text("SELECT sector_code FROM candidate_site WHERE id = :id"), {"id": rec.site_id}
    ).scalar_one()
    if principal.role is Role.SECTOR_OFFICER:
        # Officers decide small actions in their own sector; build decisions stay with planners.
        require_area(session, principal, site_sector)
        if rec.action is not Action.SUPPORT:
            raise forbidden("Only the district planner can decide this suggestion")
    else:
        require_area(session, principal, scenario.district_code)
    if rec.status is RecommendationStatus.REJECTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "This suggestion was already rejected")

    before = {"status": rec.status, "cost_rwf": rec.cost_rwf}
    edits = None
    if body.verdict is Verdict.EDIT:
        assert body.edits is not None
        unknown = set(body.edits) - EDITABLE
        if unknown:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Cannot edit {sorted(unknown)}"
            )
        new_cost = int(body.edits["cost_rwf"])
        if new_cost <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cost must be positive")
        edits = {"cost_rwf": {"from": rec.cost_rwf, "to": new_cost}}
        rec.cost_rwf = new_cost
    rec.status = {
        Verdict.APPROVE: RecommendationStatus.APPROVED,
        Verdict.EDIT: RecommendationStatus.EDITED,
        Verdict.REJECT: RecommendationStatus.REJECTED,
    }[body.verdict]
    session.add(
        Decision(
            recommendation_id=rec.id,
            user_id=principal.id,
            verdict=body.verdict,
            reason_code=body.reason_code,
            reason_text=body.reason_text,
            edits=edits,
        )
    )
    reason = " ".join(
        filter(None, [body.reason_code.value if body.reason_code else None, body.reason_text])
    )
    audit.record(
        session,
        principal,
        f"recommendation.{body.verdict.value}",
        "recommendation",
        str(rec.id),
        before=before,
        after={"status": rec.status, "cost_rwf": rec.cost_rwf, "site_id": rec.site_id},
        reason=reason or None,
    )
    session.flush()
    if body.verdict is Verdict.REJECT:
        service.rerun(session, get_settings(), scenario)
    return _envelope(session, scenario)


@router.get("/decisions", response_model=list[DecisionLogRow])
def decisions(district: str, session: SessionDep, principal: Reader) -> list[DecisionLogRow]:
    require_area(session, principal, district)
    rows = session.execute(
        text(
            "SELECT d.created_at, u.display_name AS user_name, u.role AS user_role, d.verdict, "
            "d.reason_code, d.reason_text, r.action, cs.name AS site_name, s.name AS scenario_name "
            "FROM decision d JOIN recommendation r ON r.id = d.recommendation_id "
            "JOIN scenario s ON s.id = r.scenario_id JOIN user_account u ON u.id = d.user_id "
            "JOIN candidate_site cs ON cs.id = r.site_id "
            "WHERE s.district_code = :d ORDER BY d.created_at DESC"
        ),
        {"d": district},
    ).all()
    return [DecisionLogRow.model_validate(r._mapping) for r in rows]


@router.get("/planning-defaults/{area}", response_model=PlanningDefaults)
def get_defaults(area: str, session: SessionDep, principal: Reader) -> PlanningDefaults:
    require_area(session, principal, area)
    for code in (area, "RW"):
        row = session.get(PlanningDefault, code)
        if row is not None:
            return PlanningDefaults(
                area_code=row.area_code,
                budget_rwf=row.budget_rwf,
                weights=WeightsIn(
                    stunting=row.weight_stunting,
                    readiness=row.weight_readiness,
                    jobs=row.weight_jobs,
                ),
            )
    return FALLBACK_DEFAULTS


@router.put("/planning-defaults/{area}", response_model=PlanningDefaults)
def set_defaults(
    area: str, body: PlanningDefaults, session: SessionDep, principal: Analyst
) -> PlanningDefaults:
    require_area(session, principal, area)
    row = session.get(PlanningDefault, area)
    before = None
    if row is None:
        row = PlanningDefault(area_code=area)
        session.add(row)
    else:
        before = {
            "budget_rwf": row.budget_rwf,
            "weights": [row.weight_stunting, row.weight_readiness, row.weight_jobs],
        }
    row.budget_rwf = body.budget_rwf
    row.weight_stunting = body.weights.stunting
    row.weight_readiness = body.weights.readiness
    row.weight_jobs = body.weights.jobs
    row.updated_by = principal.id
    audit.record(
        session,
        principal,
        "planning_defaults.update",
        "planning_default",
        area,
        before=before,
        after={"budget_rwf": body.budget_rwf, "weights": body.weights.model_dump()},
    )
    return PlanningDefaults(area_code=area, budget_rwf=body.budget_rwf, weights=body.weights)
