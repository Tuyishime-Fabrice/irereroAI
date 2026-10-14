"""Map layers as GeoJSON. Boundaries come pre-simplified per zoom (full, medium, coarse)."""

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from irerero_api.auth.deps import Planner
from irerero_api.auth.scope import require_district
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, RangeOut, wrap
from irerero_api.schemas.geo import (
    AreaProperties,
    CentreProperties,
    DemandProperties,
    Detail,
    Feature,
    FeatureCollection,
    SiteProperties,
)
from irerero_engine.coverage import CATCHMENT_STEPS
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/geo", tags=["geo"])
SessionDep = Annotated[Session, Depends(get_session)]
NATIONAL = "RW"
GEOMETRY = {"full": "geom", "medium": "geom_medium", "coarse": "geom_coarse"}

AREAS = """
    SELECT a.code, a.name, a.level, a.source AS geo_source, a.reference_year AS geo_year,
        a.origin AS geo_origin, ST_AsGeoJSON({geom}, 5) AS geometry, n.*,
        cs.children_covered, cs.children_uncovered, cs.overcrowded_centres,
        (SELECT count(*) FROM centre c JOIN admin_unit x ON x.code = c.sector_code
            WHERE c.sector_code = a.code OR x.parent_code = a.code) AS centres,
        (SELECT count(*) FROM demand_signal d JOIN admin_unit x ON x.code = d.sector_code
            WHERE d.sector_code = a.code OR x.parent_code = a.code) AS demand_signals
    FROM admin_unit a
    LEFT JOIN LATERAL (
        SELECT * FROM need_estimate n WHERE n.area_code = a.code
        ORDER BY n.reference_year DESC LIMIT 1
    ) n ON true
    LEFT JOIN LATERAL (
        SELECT sum(c.children_covered) AS children_covered,
            sum(c.children_uncovered) AS children_uncovered,
            sum(c.overcrowded_centres) AS overcrowded_centres
        FROM coverage_snapshot c JOIN admin_unit x ON x.code = c.area_code
        WHERE (c.area_code = a.code OR x.parent_code = a.code)
            AND c.catchment_minutes = :minutes
    ) cs ON true
    WHERE (CAST(:level AS text) IS NULL AND a.parent_code = :parent)
       OR (a.level = :level AND (a.parent_code = :parent
           OR a.parent_code IN (SELECT code FROM admin_unit WHERE parent_code = :parent)))
    ORDER BY a.code
"""


def catchment(minutes: int | None) -> int:
    """The precomputed catchment step closest to the requested minutes."""
    wanted = minutes or get_settings().catchment_minutes
    return min(CATCHMENT_STEPS, key=lambda step: (abs(step - wanted), step))


def _range(row: object, prefix: str) -> RangeOut | None:
    estimate = getattr(row, f"{prefix}_estimate", None)
    if estimate is None:
        return None
    return RangeOut(
        estimate=estimate, low=getattr(row, f"{prefix}_low"), high=getattr(row, f"{prefix}_high")
    )


def _children(row: object) -> RangeOut | None:
    young, old = _range(row, "children_0_2"), _range(row, "children_3_6")
    if young is None or old is None:
        return None
    return RangeOut(
        estimate=young.estimate + old.estimate, low=young.low + old.low, high=young.high + old.high
    )


def _uncertainty(children: RangeOut | None, stunting: RangeOut | None) -> float | None:
    widths = [(r.high - r.low) / 2 / r.estimate for r in (children, stunting) if r and r.estimate]
    return round(max(widths), 3) if widths else None


@router.get("/areas", response_model=Envelope[FeatureCollection[AreaProperties]])
def areas(
    session: SessionDep,
    principal: Planner,
    parent: str | None = None,
    detail: Detail = "medium",
    level: Literal["district", "sector"] | None = None,
    minutes: Annotated[int | None, Query(description="Catchment step in minutes")] = None,
) -> Envelope[FeatureCollection[AreaProperties]]:
    """Areas inside `parent` with need, uncertainty, coverage and demand: its direct children,
    or, with `level`, its descendants at that level. Every planner can read the national map
    (parent=RW, level=district); sector detail is limited to the planner's own district."""
    parent = parent or principal.district_code
    if not (parent == NATIONAL and level == "district"):
        require_district(session, principal, parent)
    query = text(AREAS.format(geom=f"a.{GEOMETRY[detail]}"))
    params = {"parent": parent, "level": level, "minutes": catchment(minutes)}
    rows = session.execute(query, params).all()
    features = []
    sources = []
    for row in rows:
        children, stunting = _children(row), _range(row, "stunting_risk")
        sources.append(SourceRef("admin_unit", row.geo_source, row.geo_year, row.geo_origin))
        if row.source is not None:
            sources.append(SourceRef("need_estimate", row.source, row.reference_year, row.origin))
        features.append(
            Feature[AreaProperties](
                id=row.code,
                geometry=json.loads(row.geometry),
                properties=AreaProperties(
                    code=row.code,
                    name=row.name,
                    level=row.level,
                    children=children,
                    stunting_risk=stunting,
                    mothers_barrier_share=_range(row, "mothers_barrier_share"),
                    uncertainty=_uncertainty(children, stunting),
                    children_covered=row.children_covered,
                    children_uncovered=row.children_uncovered,
                    overcrowded_centres=row.overcrowded_centres,
                    centres=row.centres,
                    demand_signals=row.demand_signals,
                    origin=row.origin,
                ),
            )
        )
    return wrap(FeatureCollection[AreaProperties](features=features), sources)


CENTRES = text(
    """
    SELECT c.code, c.name, c.type, c.capacity, c.verified, c.enrolment, c.water_available,
        c.offers_meals, c.origin, c.source, c.reference_year,
        ST_AsGeoJSON(c.location, 6) AS geometry
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE c.sector_code = :area OR s.parent_code = :area
    ORDER BY c.code
    """
)


@router.get("/centres", response_model=Envelope[FeatureCollection[CentreProperties]])
def centres(
    session: SessionDep, principal: Planner, area: str | None = None
) -> Envelope[FeatureCollection[CentreProperties]]:
    area = area or principal.district_code
    require_district(session, principal, area)
    rows = session.execute(CENTRES, {"area": area}).all()
    features = [
        Feature[CentreProperties](
            id=r.code,
            geometry=json.loads(r.geometry),
            properties=CentreProperties(
                code=r.code,
                name=r.name,
                type=r.type,
                capacity=r.capacity,
                verified=r.verified,
                enrolment=r.enrolment,
                overcrowded=r.enrolment > r.capacity,
                water_available=r.water_available,
                offers_meals=r.offers_meals,
                origin=r.origin,
            ),
        )
        for r in rows
    ]
    sources = [SourceRef("centre", r.source, r.reference_year, r.origin) for r in rows]
    return wrap(FeatureCollection[CentreProperties](features=features), sources)


DEMAND = text(
    """
    SELECT d.grid_cell, min(d.sector_code) AS sector_code,
        ST_AsGeoJSON(d.cell_centre, 6) AS geometry, count(*) AS centre_requests,
        min(d.origin) AS origin, extract(year FROM max(d.created_at))::int AS year
    FROM demand_signal d JOIN admin_unit s ON s.code = d.sector_code
    WHERE d.sector_code = :area OR s.parent_code = :area
    GROUP BY d.grid_cell, d.cell_centre ORDER BY d.grid_cell
    """
)


@router.get("/demand", response_model=Envelope[FeatureCollection[DemandProperties]])
def demand(
    session: SessionDep, principal: Planner, area: str | None = None
) -> Envelope[FeatureCollection[DemandProperties]]:
    """Parents' centre requests per 500 m cell."""
    area = area or principal.district_code
    require_district(session, principal, area)
    rows = session.execute(DEMAND, {"area": area}).all()
    features = [
        Feature[DemandProperties](
            id=r.grid_cell,
            geometry=json.loads(r.geometry),
            properties=DemandProperties(
                grid_cell=r.grid_cell,
                sector_code=r.sector_code,
                centre_requests=r.centre_requests,
            ),
        )
        for r in rows
    ]
    sources = [SourceRef("demand_signal", "Parent centre requests", r.year, r.origin) for r in rows]
    return wrap(FeatureCollection[DemandProperties](features=features), sources)


SITES = text(
    """
    SELECT s.id, s.name, s.kind, s.sector_code, s.source, s.reference_year, s.origin,
        ST_AsGeoJSON(s.location, 6) AS geometry
    FROM candidate_site s JOIN admin_unit a ON a.code = s.sector_code
    WHERE (s.sector_code = :area OR a.parent_code = :area) AND s.kind IN ('village', 'school')
    ORDER BY s.id
    """
)


@router.get("/sites", response_model=Envelope[FeatureCollection[SiteProperties]])
def sites(
    session: SessionDep, principal: Planner, area: str | None = None
) -> Envelope[FeatureCollection[SiteProperties]]:
    area = area or principal.district_code
    require_district(session, principal, area)
    rows = session.execute(SITES, {"area": area}).all()
    features = [
        Feature[SiteProperties](
            id=r.id,
            geometry=json.loads(r.geometry),
            properties=SiteProperties(id=r.id, name=r.name, kind=r.kind, sector_code=r.sector_code),
        )
        for r in rows
    ]
    sources = [SourceRef("candidate_site", r.source, r.reference_year, r.origin) for r in rows]
    return wrap(FeatureCollection[SiteProperties](features=features), sources)
