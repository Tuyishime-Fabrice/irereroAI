"""The 500 m privacy grid for parent locations.

A location is projected to EPSG:32735 and replaced by the grid cell that contains it. Only the
cell id and the cell centre are ever stored. Both the API and the demo generator use these
expressions, so they snap identically.
"""

from typing import Any

from sqlalchemy import Float, Select, cast, func, literal, select
from sqlalchemy.sql.elements import ColumnElement

from irerero_contract.base import METRIC_SRID, SRID

CELL_METRES = 500


def _projected(lon: float, lat: float) -> ColumnElement[Any]:
    point = func.ST_SetSRID(func.ST_MakePoint(literal(lon, Float), literal(lat, Float)), SRID)
    return func.ST_Transform(point, METRIC_SRID)


def _corner(coordinate: ColumnElement[Any]) -> ColumnElement[Any]:
    return func.floor(coordinate / CELL_METRES) * CELL_METRES


def cell_id(lon: float, lat: float) -> ColumnElement[str]:
    """'E{easting}N{northing}' of the cell's south-west corner, in metres."""
    projected = _projected(lon, lat)
    easting = cast(_corner(func.ST_X(projected)), Float)
    northing = cast(_corner(func.ST_Y(projected)), Float)
    return func.concat(
        "E", func.to_char(easting, "FM9999999"), "N", func.to_char(northing, "FM99999999")
    )


def cell_centre(lon: float, lat: float) -> ColumnElement[Any]:
    """Centre of the containing cell, back in EPSG:4326."""
    projected = _projected(lon, lat)
    half = CELL_METRES / 2
    centre = func.ST_SetSRID(
        func.ST_MakePoint(
            _corner(func.ST_X(projected)) + half, _corner(func.ST_Y(projected)) + half
        ),
        METRIC_SRID,
    )
    return func.ST_Transform(centre, SRID)


def nearest_sector(point: ColumnElement[Any]) -> Select[str]:
    """The sector containing a point, or the nearest one for cells that straddle a lake shore."""
    from irerero_contract.tables import AdminUnit

    return (
        select(AdminUnit.code)
        .where(AdminUnit.level == "sector")
        .order_by(func.ST_Distance(AdminUnit.geom, point))
        .limit(1)
    )
