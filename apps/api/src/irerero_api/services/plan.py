"""Planning scenarios: run the optimizer, store suggestions, and re-run after rejections.

Suggestions are never acted on here. A person approves, edits or rejects each one; approved and
edited suggestions stay fixed when the plan is re-run, rejected ones become constraints.
"""

import uuid
from collections import Counter
from collections.abc import Sequence

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from irerero_api.auth.principal import Principal
from irerero_api.config import Settings
from irerero_api.schemas.common import DriverOut, RangeOut, SourceOut
from irerero_api.schemas.plan import (
    DecisionOut,
    OutcomesOut,
    RecommendationOut,
    ScenarioIn,
    ScenarioOut,
    WeightsIn,
)
from irerero_api.services.planning import planning_input
from irerero_contract.enums import Origin, RecommendationStatus
from irerero_contract.tables import AdminUnit, Recommendation, Scenario, UserAccount
from irerero_engine.coverage import StraightLineCoverage
from irerero_engine.explain import TemplateExplainer
from irerero_engine.optimizer import (
    Candidate,
    GreedyOptimizer,
    Impact,
    Outcomes,
    Plan,
    PlanningInput,
    Weights,
    evaluate,
    largest_population_first,
)
from irerero_engine.types import Driver, Range, SourceRef

ACTIVE = (RecommendationStatus.APPROVED, RecommendationStatus.EDITED, RecommendationStatus.PROPOSED)
DECIDED = (RecommendationStatus.APPROVED, RecommendationStatus.EDITED)

SITE_SOURCES = text(
    """
    SELECT s.id, s.source AS site_source, s.reference_year AS site_year, s.origin AS site_origin,
        u.source AS cost_source, u.reference_year AS cost_year, u.origin AS cost_origin,
        n.source AS need_source, n.reference_year AS need_year, n.origin AS need_origin,
        c.source AS centre_source, c.reference_year AS centre_year, c.origin AS centre_origin
    FROM candidate_site s
    JOIN admin_unit a ON a.code = s.sector_code
    JOIN unit_cost u ON u.band = s.unit_cost_band AND u.action = CASE s.kind
        WHEN 'centre_upgrade' THEN 'upgrade' WHEN 'centre_support' THEN 'support' ELSE 'build' END
    LEFT JOIN LATERAL (SELECT * FROM need_estimate n WHERE n.area_code = s.sector_code
        ORDER BY n.reference_year DESC LIMIT 1) n ON true
    LEFT JOIN centre c ON c.code = s.centre_code
    WHERE a.parent_code = :district
    """
)


def coverage_model(settings: Settings) -> StraightLineCoverage:
    return StraightLineCoverage(settings.catchment_minutes, settings.metres_per_minute)


def weights_of(weights: WeightsIn) -> Weights:
    return Weights(weights.stunting, weights.readiness, weights.jobs)


def build_input(
    session: Session,
    settings: Settings,
    district: str,
    budget: float,
    weights: WeightsIn,
    excluded: frozenset[str] = frozenset(),
    preselected: tuple[str, ...] = (),
) -> PlanningInput:
    data = planning_input(
        session.connection(),
        district,
        budget,
        weights_of(weights),
        coverage_model(settings),
        excluded,
    )
    return PlanningInput(
        points=data.points,
        base_state=data.base_state,
        candidates=data.candidates,
        weights=data.weights,
        constraints=data.constraints,
        child_count_bounds=data.child_count_bounds,
        preselected=preselected,
    )


def rounded(value: Range) -> RangeOut:
    return RangeOut(estimate=round(value.estimate), low=round(value.low), high=round(value.high))


def outcomes_out(outcomes: Outcomes, chosen: Sequence[Candidate]) -> OutcomesOut:
    return OutcomesOut(
        children_reached=rounded(outcomes.children_reached),
        uncovered_remaining=rounded(outcomes.uncovered_remaining),
        high_risk_reached=rounded(outcomes.high_risk_reached),
        mothers_under3_reached=rounded(outcomes.mothers_under3_reached),
        children_supported=round(outcomes.children_supported),
        cost_rwf=outcomes.cost,
        actions=dict(Counter(c.action.value for c in chosen)),
    )


def site_sources(session: Session, district: str) -> dict[str, list[SourceRef]]:
    result: dict[str, list[SourceRef]] = {}
    for r in session.execute(SITE_SOURCES, {"district": district}):
        refs = [
            SourceRef("candidate_site", r.site_source, r.site_year, r.site_origin),
            SourceRef("unit_cost", r.cost_source, r.cost_year, r.cost_origin),
        ]
        if r.need_source:
            refs.append(SourceRef("need_estimate", r.need_source, r.need_year, r.need_origin))
        if r.centre_source:
            refs.append(SourceRef("centre", r.centre_source, r.centre_year, r.centre_origin))
        result[r.id] = refs
    return result


def _store(
    session: Session,
    scenario: Scenario,
    plan: Plan,
    sources: dict[str, list[SourceRef]],
    skip: set[str],
) -> None:
    for suggestion in plan.suggestions:
        candidate = suggestion.candidate
        if candidate.id in skip:
            continue
        impact = suggestion.impact
        session.add(
            Recommendation(
                scenario_id=scenario.id,
                rank=suggestion.rank,
                action=candidate.action.value,
                site_id=candidate.id,
                children_reached=round(impact.children_reached.estimate),
                reached_low=round(impact.children_reached.low),
                reached_high=round(impact.children_reached.high),
                high_risk_children_reached=round(impact.high_risk_reached.estimate),
                mothers_under3_reached=round(impact.mothers_under3_reached.estimate),
                cost_rwf=round(candidate.cost.estimate),
                score=suggestion.score,
                drivers=[d.__dict__ for d in suggestion.drivers],
                sources=[s.__dict__ for s in sources.get(candidate.id, [])],
            )
        )


def create(
    session: Session, settings: Settings, principal: Principal, body: ScenarioIn
) -> Scenario:
    data = build_input(
        session,
        settings,
        body.district_code,
        body.budget_rwf,
        body.weights,
        frozenset(body.excluded_site_ids),
    )
    optimizer = GreedyOptimizer(coverage_model(settings))
    plan = optimizer.plan(data)
    sources = site_sources(session, body.district_code)
    simulated = any(s.origin == Origin.SIMULATED.value for refs in sources.values() for s in refs)
    scenario = Scenario(
        district_code=body.district_code,
        name=body.name,
        budget_rwf=body.budget_rwf,
        weight_stunting=body.weights.stunting,
        weight_readiness=body.weights.readiness,
        weight_jobs=body.weights.jobs,
        constraints={"excluded_site_ids": body.excluded_site_ids},
        model_version_id=optimizer.version,
        origin=Origin.SIMULATED if simulated else Origin.OFFICIAL,
        created_by=principal.id,
    )
    session.add(scenario)
    session.flush()
    _store(session, scenario, plan, sources, skip=set())
    session.flush()
    return scenario


def _weights_in(scenario: Scenario) -> WeightsIn:
    return WeightsIn(
        stunting=scenario.weight_stunting,
        readiness=scenario.weight_readiness,
        jobs=scenario.weight_jobs,
    )


def recommendations(
    session: Session, scenario_id: uuid.UUID, statuses: Sequence[RecommendationStatus]
) -> list[Recommendation]:
    return list(
        session.scalars(
            select(Recommendation)
            .where(Recommendation.scenario_id == scenario_id, Recommendation.status.in_(statuses))
            .order_by(Recommendation.rank)
        )
    )


def rerun(session: Session, settings: Settings, scenario: Scenario) -> None:
    """Refill the plan after a rejection, keeping every approved or edited suggestion."""
    decided = recommendations(session, scenario.id, DECIDED)
    data = build_input(
        session,
        settings,
        scenario.district_code,
        scenario.budget_rwf,
        _weights_in(scenario),
        frozenset(scenario.constraints.get("excluded_site_ids", [])),
        preselected=tuple(r.site_id for r in decided),
    )
    plan = GreedyOptimizer(coverage_model(settings)).plan(data)
    session.execute(
        delete(Recommendation).where(
            Recommendation.scenario_id == scenario.id,
            Recommendation.status == RecommendationStatus.PROPOSED,
        )
    )
    by_site = {r.site_id: r for r in decided}
    for suggestion in plan.suggestions:
        if suggestion.candidate.id in by_site:
            by_site[suggestion.candidate.id].rank = suggestion.rank
    # Rejected rows keep their history; renumber them after the active list.
    for offset, row in enumerate(
        recommendations(session, scenario.id, (RecommendationStatus.REJECTED,))
    ):
        row.rank = len(plan.suggestions) + offset + 1
    _store(
        session, scenario, plan, site_sources(session, scenario.district_code), skip=set(by_site)
    )
    session.flush()


def _decisions(session: Session, recommendation_id: uuid.UUID) -> list[DecisionOut]:
    rows = session.execute(
        text(
            "SELECT d.*, u.display_name AS user_name, u.role AS user_role FROM decision d "
            "JOIN user_account u ON u.id = d.user_id WHERE d.recommendation_id = :id "
            "ORDER BY d.created_at"
        ),
        {"id": recommendation_id},
    ).all()
    return [DecisionOut.model_validate(r._mapping) for r in rows]


def _rec_out(
    session: Session,
    rec: Recommendation,
    candidate: Candidate,
    impact: Impact | None,
    names: dict[str, str],
    lonlat: dict[str, tuple[float, float]],
    catchment_minutes: int,
) -> RecommendationOut:
    """`impact` is today's evaluation for active suggestions; rejected ones keep stored values."""
    drivers = [Driver(**d) for d in rec.drivers]
    reached = (
        impact.children_reached
        if impact
        else Range(rec.children_reached, rec.reached_low, rec.reached_high)
    )
    high_risk = impact.high_risk_reached if impact else Range(*[rec.high_risk_children_reached] * 3)
    mothers = impact.mothers_under3_reached if impact else Range(*[rec.mothers_under3_reached] * 3)
    numbers = {
        "reached": reached.estimate,
        "reached_low": reached.low,
        "reached_high": reached.high,
        "high_risk": high_risk.estimate,
        "mothers": mothers.estimate,
        "cost": rec.cost_rwf,
        "supported": candidate.support_children,
    }
    en, rw = TemplateExplainer().suggestion(
        rec.action.value, candidate.name, numbers, drivers, catchment_minutes
    )
    ratio = rec.cost_rwf / candidate.cost.estimate if candidate.cost.estimate else 1.0
    lon, lat = lonlat[candidate.id]
    return RecommendationOut(
        id=rec.id,
        rank=rec.rank,
        action=rec.action,
        site_id=rec.site_id,
        site_name=candidate.name,
        sector_code=candidate.area_code,
        sector_name=names.get(candidate.area_code, candidate.area_code),
        centre_code=candidate.centre_code,
        lon=lon,
        lat=lat,
        children_reached=rounded(reached),
        high_risk_children_reached=rounded(high_risk),
        mothers_under3_reached=rounded(mothers),
        children_supported=round(candidate.support_children)
        if rec.action.value == "support"
        else 0,
        cost=RangeOut.of(candidate.cost.scaled(ratio)),
        drivers=[DriverOut.of(d) for d in drivers],
        sources=[SourceOut(**s) for s in rec.sources],
        status=rec.status,
        explanation_en=en,
        explanation_rw=rw,
        decisions=_decisions(session, rec.id),
    )


def scenario_out(session: Session, settings: Settings, scenario: Scenario) -> ScenarioOut:
    data = build_input(
        session, settings, scenario.district_code, scenario.budget_rwf, _weights_in(scenario)
    )
    model = coverage_model(settings)
    by_id = {c.id: c for c in data.candidates}
    names = {
        row.code: row.name
        for row in session.execute(
            select(AdminUnit.code, AdminUnit.name).where(
                AdminUnit.parent_code == scenario.district_code
            )
        )
    }
    lonlat = {
        r.id: (r.lon, r.lat)
        for r in session.execute(
            text(
                "SELECT s.id, ST_X(s.location) AS lon, ST_Y(s.location) AS lat "
                "FROM candidate_site s JOIN admin_unit a ON a.code = s.sector_code "
                "WHERE a.parent_code = :d"
            ),
            {"d": scenario.district_code},
        )
    }
    active = recommendations(session, scenario.id, ACTIVE)
    rejected = recommendations(session, scenario.id, (RecommendationStatus.REJECTED,))
    chosen = [by_id[r.site_id] for r in active]
    evaluation = evaluate(model, data, chosen)
    baseline = largest_population_first(model, data)
    district = session.get(AdminUnit, scenario.district_code)
    creator = session.get(UserAccount, scenario.created_by)
    minutes = settings.catchment_minutes
    return ScenarioOut(
        id=scenario.id,
        district_code=scenario.district_code,
        district_name=district.name if district else scenario.district_code,
        name=scenario.name,
        budget_rwf=scenario.budget_rwf,
        weights=_weights_in(scenario),
        created_at=scenario.created_at,
        created_by_name=creator.display_name if creator else "",
        origin=scenario.origin,
        optimizer_version=scenario.model_version_id,
        catchment_minutes=minutes,
        recommendations=[
            _rec_out(session, r, by_id[r.site_id], impact, names, lonlat, minutes)
            for r, impact in zip(active, evaluation.impacts, strict=True)
        ],
        rejected=[
            _rec_out(session, r, by_id[r.site_id], None, names, lonlat, minutes) for r in rejected
        ],
        outcomes=outcomes_out(evaluation.outcomes, chosen),
        baseline=outcomes_out(baseline.outcomes, [s.candidate for s in baseline.suggestions]),
    )


def outcomes_out_for(
    session: Session, settings: Settings, scenario: Scenario, items: Sequence[RecommendationOut]
) -> OutcomesOut:
    """Outcomes of a subset of a scenario's suggestions, e.g. only the approved ones."""
    data = build_input(
        session, settings, scenario.district_code, scenario.budget_rwf, _weights_in(scenario)
    )
    by_id = {c.id: c for c in data.candidates}
    chosen = [by_id[item.site_id] for item in items]
    return outcomes_out(evaluate(coverage_model(settings), data, chosen).outcomes, chosen)
