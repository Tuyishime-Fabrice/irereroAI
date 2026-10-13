"""National view: all districts with ranges, model and pipeline status, aggregate export."""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.calendar import current_week
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, RangeOut, wrap
from irerero_api.suppression import suppress_csv
from irerero_contract.enums import EngineComponent, Origin, Role
from irerero_contract.tables import ModelVersion
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/national", tags=["national"])
SessionDep = Annotated[Session, Depends(get_session)]
Analyst = Annotated[Principal, Depends(require_roles(Role.NATIONAL_ANALYST, Role.ADMIN))]

DISTRICTS = text(
    """
    SELECT a.code, a.name, p.name AS province, n.*,
        (SELECT count(*) FROM centre c JOIN admin_unit s ON s.code = c.sector_code
            WHERE s.parent_code = a.code) AS centres,
        cs.children_covered, cs.children_uncovered
    FROM admin_unit a JOIN admin_unit p ON p.code = a.parent_code
    LEFT JOIN LATERAL (SELECT * FROM need_estimate n WHERE n.area_code = a.code
        ORDER BY n.reference_year DESC LIMIT 1) n ON true
    LEFT JOIN LATERAL (
        SELECT sum(c.children_covered) AS children_covered,
            sum(c.children_uncovered) AS children_uncovered
        FROM coverage_snapshot c JOIN admin_unit s ON s.code = c.area_code
        WHERE s.parent_code = a.code AND c.week_start = :week
    ) cs ON true
    WHERE a.level = 'district' ORDER BY a.name
    """
)


class DistrictRow(BaseModel):
    code: str
    name: str
    province: str
    children: RangeOut
    stunting_risk: RangeOut
    mothers_barrier_share: RangeOut
    uncertainty: float
    centres: int
    children_covered: int | None
    children_uncovered: int | None
    deep_data: bool
    origin: Origin


def _rows(session: Session) -> list[DistrictRow]:
    out = []
    for r in session.execute(DISTRICTS, {"week": current_week(get_settings())}):
        children = RangeOut(
            estimate=r.children_0_2_estimate + r.children_3_6_estimate,
            low=r.children_0_2_low + r.children_3_6_low,
            high=r.children_0_2_high + r.children_3_6_high,
        )
        stunting = RangeOut(
            estimate=r.stunting_risk_estimate, low=r.stunting_risk_low, high=r.stunting_risk_high
        )
        widths = [(x.high - x.low) / 2 / x.estimate for x in (children, stunting) if x.estimate]
        out.append(
            DistrictRow(
                code=r.code,
                name=r.name,
                province=r.province,
                children=children,
                stunting_risk=stunting,
                mothers_barrier_share=RangeOut(
                    estimate=r.mothers_barrier_share_estimate,
                    low=r.mothers_barrier_share_low,
                    high=r.mothers_barrier_share_high,
                ),
                uncertainty=round(max(widths, default=0.0), 3),
                centres=r.centres,
                children_covered=r.children_covered,
                children_uncovered=r.children_uncovered,
                deep_data=r.children_covered is not None,
                origin=r.origin,
            )
        )
    return out


def _sources(session: Session) -> list[SourceRef]:
    rows = session.execute(
        text(
            "SELECT DISTINCT n.source, n.reference_year, n.origin FROM need_estimate n "
            "JOIN admin_unit a ON a.code = n.area_code WHERE a.level = 'district'"
        )
    ).all()
    return [SourceRef("need_estimate", r.source, r.reference_year, r.origin) for r in rows]


@router.get("/districts", response_model=Envelope[list[DistrictRow]])
def districts(session: SessionDep, principal: Analyst) -> Envelope[list[DistrictRow]]:
    return wrap(_rows(session), _sources(session))


@router.get("/export.csv", response_class=StreamingResponse)
def export_csv(session: SessionDep, principal: Analyst) -> StreamingResponse:
    """District aggregates. Counts below 5 are written as <5. Every row states its origin."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "district_code",
            "district",
            "province",
            "children_0_6_estimate",
            "children_0_6_low",
            "children_0_6_high",
            "stunting_risk_estimate",
            "stunting_risk_low",
            "stunting_risk_high",
            "centres",
            "children_covered",
            "children_uncovered",
            "origin",
        ]
    )
    for r in _rows(session):
        writer.writerow(
            [
                r.code,
                r.name,
                r.province,
                suppress_csv(r.children.estimate),
                suppress_csv(r.children.low),
                suppress_csv(r.children.high),
                round(r.stunting_risk.estimate, 3),
                round(r.stunting_risk.low, 3),
                round(r.stunting_risk.high, 3),
                suppress_csv(r.centres),
                suppress_csv(r.children_covered),
                suppress_csv(r.children_uncovered),
                r.origin.value,
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="irereroai-districts.csv"'},
    )


class ModelVersionOut(BaseModel):
    id: str
    component: EngineComponent
    description: str
    params: dict[str, object]
    metrics: dict[str, object]


@router.get("/models", response_model=list[ModelVersionOut])
def models(session: SessionDep, principal: Analyst) -> list[ModelVersionOut]:
    rows = session.scalars(select(ModelVersion).order_by(ModelVersion.component)).all()
    return [ModelVersionOut.model_validate(r, from_attributes=True) for r in rows]
