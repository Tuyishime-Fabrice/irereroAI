"""Public endpoints: no sign-in. Never expose internal report data beyond free places."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Row, select, text
from sqlalchemy.orm import Session

from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.schemas.geo import Feature, FeatureCollection
from irerero_api.schemas.public import (
    AgeBand,
    DataSourceOut,
    DemandRecorded,
    DemandRequest,
    District,
    FindResult,
    Methodology,
    PipelineRunOut,
    Place,
    PublicCentre,
)
from irerero_api.services.demand import record_demand
from irerero_api.suppression import suppress
from irerero_contract.enums import DemandKind, FeeBand, Origin
from irerero_contract.tables import DataSource, PipelineRun
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/public", tags=["public"])
SessionDep = Annotated[Session, Depends(get_session)]
FEE_ORDER = list(FeeBand)

CENTRES = text(
    """
    SELECT c.code, c.name, c.type, s.name AS sector_name, ST_X(c.location) AS lon,
        ST_Y(c.location) AS lat, c.serves_0_2, c.serves_3_6, c.opening_hours, c.fee_band,
        c.offers_meals, c.offers_growth_monitoring, c.disability_inclusive, c.capacity,
        c.verified_at, c.origin, c.source, c.reference_year,
        CASE WHEN CAST(:lon AS float) IS NULL THEN NULL ELSE ST_Distance(
            ST_Transform(c.location, 32735),
            ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32735)) / 1000 END AS km,
        (SELECT c.capacity - (r.enrolled_0_2_female + r.enrolled_0_2_male
            + r.enrolled_3_6_female + r.enrolled_3_6_male)
         FROM weekly_report r WHERE r.centre_code = c.code
         ORDER BY r.week_start DESC LIMIT 1) AS free_places
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE c.verified AND c.status = 'active' AND (CAST(:code AS text) IS NULL OR c.code = :code)
    ORDER BY km NULLS LAST, c.name
    """
)


def _public(row: Row[Any]) -> PublicCentre:
    m = row._mapping
    free = m["free_places"]
    return PublicCentre(
        code=m["code"],
        name=m["name"],
        type=m["type"],
        sector_name=m["sector_name"],
        lon=round(m["lon"], 5),
        lat=round(m["lat"], 5),
        distance_km=None if m["km"] is None else round(m["km"], 1),
        serves_0_2=m["serves_0_2"],
        serves_3_6=m["serves_3_6"],
        opening_hours=m["opening_hours"],
        fee_band=m["fee_band"],
        offers_meals=m["offers_meals"],
        offers_growth_monitoring=m["offers_growth_monitoring"],
        disability_inclusive=m["disability_inclusive"],
        capacity=suppress(m["capacity"]),
        free_places=None if free is None else suppress(max(free, 0)),
        verified_at=m["verified_at"],
        origin=m["origin"],
    )


@router.get("/centres", response_model=Envelope[FindResult])
def find_centres(
    session: SessionDep,
    lon: Annotated[float, Query(ge=28.8, le=31.0)],
    lat: Annotated[float, Query(ge=-2.9, le=-1.0)],
    radius_km: Annotated[float, Query(gt=0, le=30)] = 5,
    age_band: AgeBand | None = None,
    meals: bool = False,
    max_fee: FeeBand | None = None,
) -> Envelope[FindResult]:
    rows = session.execute(CENTRES, {"lon": lon, "lat": lat, "code": None}).all()
    allowed_fees = FEE_ORDER[: FEE_ORDER.index(max_fee) + 1] if max_fee else FEE_ORDER
    matches = [
        r
        for r in rows
        if r.km <= radius_km
        and (age_band != "0_2" or r.serves_0_2)
        and (age_band != "3_6" or r.serves_3_6)
        and (not meals or r.offers_meals)
        and FeeBand(r.fee_band) in allowed_fees
    ]
    recorded = False
    if not matches:
        origin = Origin.SIMULATED if get_settings().demo_mode else Origin.PARTNER
        record_demand(session, DemandKind.EMPTY_SEARCH, lon, lat, age_band, origin)
        recorded = True
    sources = [SourceRef("centre", r.source, r.reference_year, r.origin) for r in matches]
    return wrap(
        FindResult(centres=[_public(r) for r in matches], demand_recorded=recorded), sources
    )


@router.get("/centres/{code}", response_model=Envelope[PublicCentre])
def centre_detail(code: str, session: SessionDep) -> Envelope[PublicCentre]:
    row = session.execute(CENTRES, {"lon": None, "lat": None, "code": code}).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No verified centre with that code")
    return wrap(_public(row), [SourceRef("centre", row.source, row.reference_year, row.origin)])


@router.post("/demand", response_model=DemandRecorded, status_code=status.HTTP_201_CREATED)
def request_centre(body: DemandRequest, session: SessionDep) -> DemandRecorded:
    origin = Origin.SIMULATED if get_settings().demo_mode else Origin.PARTNER
    cell, sector = record_demand(
        session, DemandKind.CENTRE_REQUEST, body.lon, body.lat, body.age_band, origin
    )
    return DemandRecorded(grid_cell=cell, sector_name=sector)


@router.get("/methodology", response_model=Methodology)
def methodology(session: SessionDep) -> Methodology:
    sources = session.scalars(select(DataSource).order_by(DataSource.status, DataSource.id)).all()
    runs = session.scalars(select(PipelineRun).order_by(PipelineRun.started_at)).all()
    return Methodology(
        sources=[DataSourceOut.model_validate(s, from_attributes=True) for s in sources],
        runs=[
            PipelineRunOut(
                id=str(r.id),
                pipeline=r.pipeline,
                origin=r.origin,
                status=r.status,
                started_at=r.started_at,
                finished_at=r.finished_at,
                code_version=r.code_version,
                row_counts=r.row_counts,
                checks=r.checks,
            )
            for r in runs
        ],
    )


@router.get("/places", response_model=list[District])
def places(session: SessionDep) -> list[District]:
    """Districts and their sectors with a central point, for the place picker."""
    rows = session.execute(
        text(
            "SELECT a.code, a.name, a.level, a.parent_code, ST_X(a.centroid) AS lon, "
            "ST_Y(a.centroid) AS lat FROM admin_unit a "
            "WHERE a.level IN ('district', 'sector') ORDER BY a.name"
        )
    ).all()
    districts = {
        r.code: District(code=r.code, name=r.name, lon=r.lon, lat=r.lat, sectors=[])
        for r in rows
        if r.level == "district"
    }
    for r in rows:
        if r.level == "sector" and r.parent_code in districts:
            districts[r.parent_code].sectors.append(
                Place(code=r.code, name=r.name, lon=r.lon, lat=r.lat)
            )
    return list(districts.values())


class Outline(BaseModel):
    code: str
    name: str


@router.get("/outlines", response_model=FeatureCollection[Outline])
def outlines(district: str, session: SessionDep) -> FeatureCollection[Outline]:
    """Sector boundaries of a district, so maps work without a basemap. Public data only."""
    rows = session.execute(
        text(
            "SELECT code, name, ST_AsGeoJSON(geom_medium, 5) AS geometry FROM admin_unit "
            "WHERE parent_code = :d AND level = 'sector' ORDER BY code"
        ),
        {"d": district},
    ).all()
    return FeatureCollection[Outline](
        features=[
            Feature[Outline](
                id=r.code,
                geometry=json.loads(r.geometry),
                properties=Outline(code=r.code, name=r.name),
            )
            for r in rows
        ]
    )
