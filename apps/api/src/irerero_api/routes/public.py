"""Public endpoints for parents: no sign-in, no personal data, small counts withheld."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import Row, select, text
from sqlalchemy.orm import Session

from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.schemas.common import Envelope, wrap
from irerero_api.schemas.geo import Feature, FeatureCollection
from irerero_api.schemas.public import (
    DataSourceOut,
    DemandRecorded,
    DemandRequest,
    District,
    Methodology,
    PipelineRunOut,
    Place,
    PublicCentre,
)
from irerero_api.services.demand import record_demand
from irerero_api.suppression import suppress
from irerero_contract.enums import Origin
from irerero_contract.tables import DataSource, PipelineRun
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/public", tags=["public"])
SessionDep = Annotated[Session, Depends(get_session)]

NEARBY = text(
    """
    SELECT c.code, c.name, c.type, s.name AS sector_name, ST_X(c.location) AS lon,
        ST_Y(c.location) AS lat, c.serves_0_2, c.serves_3_6, c.offers_meals, c.capacity,
        c.enrolment, c.origin, c.source, c.reference_year,
        ST_Distance(ST_Transform(c.location, 32735),
            ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32735)) AS metres
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE c.verified AND c.status = 'active'
    ORDER BY metres
    LIMIT :limit
    """
)


def _public(row: Row[Any], metres_per_minute: float) -> PublicCentre:
    m = row._mapping
    return PublicCentre(
        code=m["code"],
        name=m["name"],
        type=m["type"],
        sector_name=m["sector_name"],
        lon=round(m["lon"], 5),
        lat=round(m["lat"], 5),
        distance_km=round(m["metres"] / 1000, 1),
        walking_minutes=round(m["metres"] / metres_per_minute),
        serves_0_2=m["serves_0_2"],
        serves_3_6=m["serves_3_6"],
        offers_meals=m["offers_meals"],
        capacity=suppress(m["capacity"]),
        free_places=suppress(max(m["capacity"] - m["enrolment"], 0)),
        origin=m["origin"],
    )


@router.get("/nearby", response_model=Envelope[list[PublicCentre]])
def nearby(
    session: SessionDep,
    lon: Annotated[float, Query(ge=28.8, le=31.0)],
    lat: Annotated[float, Query(ge=-2.9, le=-1.0)],
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
) -> Envelope[list[PublicCentre]]:
    """The nearest verified centres to a place, so a parent sees what exists before asking."""
    rows = session.execute(NEARBY, {"lon": lon, "lat": lat, "limit": limit}).all()
    speed = get_settings().metres_per_minute
    sources = [SourceRef("centre", r.source, r.reference_year, r.origin) for r in rows]
    return wrap([_public(r, speed) for r in rows], sources)


@router.post("/demand", response_model=DemandRecorded, status_code=status.HTTP_201_CREATED)
def request_centre(body: DemandRequest, session: SessionDep) -> DemandRecorded:
    origin = Origin.SIMULATED if get_settings().demo_mode else Origin.PARTNER
    cell, sector = record_demand(session, body.lon, body.lat, body.age_band, origin)
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
