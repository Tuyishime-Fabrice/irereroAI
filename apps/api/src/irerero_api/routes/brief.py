"""District brief: the approved plan with its reasons and sources, for printing."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from irerero_api.auth.deps import Planner
from irerero_api.auth.scope import require_district
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, RangeOut, wrap
from irerero_api.schemas.plan import OutcomesOut, RecommendationOut
from irerero_api.services import plan as plan_service
from irerero_contract.enums import RecommendationStatus
from irerero_contract.tables import AdminUnit, Scenario
from irerero_engine.types import SourceRef

router = APIRouter(tags=["plan"])
SessionDep = Annotated[Session, Depends(get_session)]


class Brief(BaseModel):
    district_code: str
    district_name: str
    as_of: date
    scenario_name: str
    budget_rwf: int
    children: RangeOut
    stunting_risk: RangeOut
    overcrowded_centres: int
    demand_signals: int
    approved: list[RecommendationOut]
    outcomes: OutcomesOut
    decided_by: list[str]


@router.get("/brief", response_model=Envelope[Brief])
def brief(district: str, session: SessionDep, principal: Planner) -> Envelope[Brief]:
    require_district(session, principal, district)
    scenario = session.scalars(
        select(Scenario)
        .where(Scenario.district_code == district)
        .order_by(Scenario.created_at.desc())
    ).first()
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run a plan first")
    settings = get_settings()
    out = plan_service.scenario_out(session, settings, scenario)
    approved = [
        r
        for r in out.recommendations
        if r.status in (RecommendationStatus.APPROVED, RecommendationStatus.EDITED)
    ]
    need = session.execute(
        text(
            "SELECT * FROM need_estimate WHERE area_code = :d ORDER BY reference_year DESC LIMIT 1"
        ),
        {"d": district},
    ).one()
    counts = session.execute(
        text(
            "SELECT (SELECT count(*) FROM centre c JOIN admin_unit s ON s.code = c.sector_code "
            "WHERE s.parent_code = :d AND c.enrolment > c.capacity) AS crowded, "
            "(SELECT count(*) FROM demand_signal d JOIN admin_unit s ON s.code = d.sector_code "
            "WHERE s.parent_code = :d) AS demand"
        ),
        {"d": district},
    ).one()
    district_unit = session.get(AdminUnit, district)
    data = Brief(
        district_code=district,
        district_name=district_unit.name if district_unit else district,
        as_of=scenario.created_at.date(),
        scenario_name=scenario.name,
        budget_rwf=scenario.budget_rwf,
        children=RangeOut(
            estimate=need.children_0_2_estimate + need.children_3_6_estimate,
            low=need.children_0_2_low + need.children_3_6_low,
            high=need.children_0_2_high + need.children_3_6_high,
        ),
        stunting_risk=RangeOut(
            estimate=need.stunting_risk_estimate,
            low=need.stunting_risk_low,
            high=need.stunting_risk_high,
        ),
        overcrowded_centres=counts.crowded,
        demand_signals=counts.demand,
        approved=approved,
        outcomes=plan_service.outcomes_out_for(session, settings, scenario, approved),
        decided_by=sorted({d.user_name for r in approved for d in r.decisions}),
    )
    sources = [SourceRef("need_estimate", need.source, need.reference_year, need.origin)] + [
        SourceRef(s.table, s.source, s.reference_year, s.origin.value)
        for r in approved
        for s in r.sources
    ]
    return wrap(data, sources)
