"""Coverage per sector for every catchment step, precomputed so the map answers instantly."""

from collections import defaultdict

from sqlalchemy import Connection, insert, text

from irerero_api.engine_io.catchments import walking_minutes
from irerero_api.engine_io.centres import seats
from irerero_api.engine_io.points import demand_points
from irerero_contract.enums import Origin
from irerero_contract.tables import CoverageSnapshot
from irerero_engine.coverage import CATCHMENT_STEPS, CatchmentCoverage, cover

OVERCROWDED = text(
    """
    SELECT c.sector_code, count(*) AS n FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district AND c.status = 'active' AND c.enrolment > c.capacity
    GROUP BY c.sector_code
    """
)


def snapshot(
    conn: Connection, district: str, origin: Origin, source: str, reference_year: int
) -> int:
    """Write one coverage_snapshot row per sector and catchment step. Returns rows written."""
    points, _ = demand_points(conn, district)
    centre_seats = seats(conn, district)
    minutes = walking_minutes(conn, district)
    crowded: dict[str, int] = {
        row.sector_code: row.n for row in conn.execute(OVERCROWDED, {"district": district})
    }
    children: dict[str, float] = defaultdict(float)
    for point in points:
        children[point.area_code] += point.children
    rows = []
    for step in CATCHMENT_STEPS:
        model = CatchmentCoverage(step, minutes)
        state = cover(model, centre_seats, points)
        uncovered: dict[str, float] = defaultdict(float)
        for point in points:
            uncovered[point.area_code] += state.uncovered(point.id)
        rows += [
            {
                "area_code": area,
                "model_version_id": model.version,
                "children_covered": round(children[area] - uncovered[area]),
                "children_uncovered": round(uncovered[area]),
                "overcrowded_centres": crowded.get(area, 0),
                "catchment_minutes": step,
                "source": source,
                "reference_year": reference_year,
                "origin": origin,
            }
            for area in sorted(children)
        ]
    conn.execute(insert(CoverageSnapshot), rows)
    return len(rows)
