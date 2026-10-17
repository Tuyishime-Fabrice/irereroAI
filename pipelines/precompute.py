"""Work out once, at build time, what the planner's map and optimizer read many times."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, insert, text

from irerero_contract.tables import Catchment
from irerero_engine.coverage import catchments
from irerero_engine.travel import TravelTimes
from irerero_engine.types import Position

# Nearest-centre times are worth knowing even beyond the longest catchment.
NEAREST_CENTRE_LIMIT = 240

EVEN_CELLS = text(
    """
    INSERT INTO population_cell (id, sector_code, location, share, source, reference_year,
        origin)
    WITH sector AS (
        SELECT code, ST_Transform(geom, 32735) AS g, reference_year, origin FROM admin_unit
        WHERE level = 'sector' AND parent_code = ANY(:districts)
    ), cell AS (
        SELECT s.code, s.g, s.reference_year, s.origin, grid.geom AS square,
            ST_Intersection(grid.geom, s.g) AS part
        FROM sector s, ST_SquareGrid(500, s.g) AS grid
        WHERE ST_Intersects(grid.geom, s.g)
    )
    SELECT code || ':' || 'E' || ST_XMin(square)::bigint || 'N' || ST_YMin(square)::bigint, code,
        ST_Transform(ST_PointOnSurface(part), 4326), ST_Area(part) / ST_Area(g),
        'Even spread over each sector (WorldPop not loaded)', reference_year, origin
    FROM cell WHERE NOT ST_IsEmpty(part) AND ST_Area(part) > 0
    """
)
CELLS = text(
    """
    SELECT c.id, ST_X(ST_Transform(c.location, 32735)) AS x,
        ST_Y(ST_Transform(c.location, 32735)) AS y
    FROM population_cell c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = ANY(:districts) ORDER BY c.id
    """
)
SEATS = text(
    """
    SELECT c.code AS id, ST_X(ST_Transform(c.location, 32735)) AS x,
        ST_Y(ST_Transform(c.location, 32735)) AS y
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = ANY(:districts) AND c.status = 'active'
    UNION ALL
    SELECT c.id, ST_X(ST_Transform(c.location, 32735)), ST_Y(ST_Transform(c.location, 32735))
    FROM candidate_site c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = ANY(:districts)
    ORDER BY id
    """
)
SITES = text(
    """
    SELECT c.id, c.centre_code, ST_X(ST_Transform(c.location, 32735)) AS x,
        ST_Y(ST_Transform(c.location, 32735)) AS y
    FROM candidate_site c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = ANY(:districts) ORDER BY c.id
    """
)
CENTRES = text(
    """
    SELECT c.code, ST_X(ST_Transform(c.location, 32735)) AS x,
        ST_Y(ST_Transform(c.location, 32735)) AS y
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = ANY(:districts) AND c.status = 'active' ORDER BY c.code
    """
)


@dataclass(frozen=True)
class Place:
    id: str
    position: Position


def even_population_cells(conn: Connection, districts: Sequence[str]) -> int:
    """Without WorldPop, children are spread evenly over each sector's area."""
    return conn.execute(EVEN_CELLS, {"districts": list(districts)}).rowcount


def _places(conn: Connection, query: object, districts: Sequence[str]) -> list[Place]:
    return [
        Place(row.id, Position(row.x, row.y))
        for row in conn.execute(query, {"districts": list(districts)})  # type: ignore[call-overload]
    ]


def walking_catchments(conn: Connection, districts: Sequence[str], travel: TravelTimes) -> int:
    seats = _places(conn, SEATS, districts)
    cells = _places(conn, CELLS, districts)
    minutes = catchments(travel, seats, cells)
    rows = [
        {"seat_id": seat, "cell_id": cell, "walk_minutes": round(m, 2), "method": travel.method}
        for seat, by_cell in minutes.items()
        for cell, m in by_cell.items()
    ]
    for start in range(0, len(rows), 10_000):
        conn.execute(insert(Catchment), rows[start : start + 10_000])
    return len(rows)


def nearest_centre_minutes(conn: Connection, districts: Sequence[str], travel: TravelTimes) -> int:
    """Walking minutes from each candidate site to the nearest other active centre."""
    centres = [
        (row.code, Position(row.x, row.y))
        for row in conn.execute(CENTRES, {"districts": list(districts)})
    ]
    updates = []
    for site in conn.execute(SITES, {"districts": list(districts)}):
        others = [p for code, p in centres if code != site.centre_code]
        times = [
            t
            for t in travel.minutes(Position(site.x, site.y), others, NEAREST_CENTRE_LIMIT)
            if t is not None
        ]
        updates.append({"id": site.id, "minutes": round(min(times)) if times else None})
    if updates:
        conn.execute(
            text("UPDATE candidate_site SET nearest_centre_minutes = :minutes WHERE id = :id"),
            updates,
        )
    return len(updates)
