from collections import defaultdict
from datetime import date

from sqlalchemy import Connection, insert, text

from irerero_api.engine_io.centres import seats
from irerero_api.engine_io.points import demand_points
from irerero_contract.enums import Origin
from irerero_contract.tables import CoverageSnapshot
from irerero_engine.coverage import CoverageModel, cover

OVERCROWDED = text(
    """
    SELECT c.sector_code, count(*) AS n FROM weekly_report r JOIN centre c ON c.code = r.centre_code
    JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district AND r.week_start = :week AND r.avg_daily_attendance > c.capacity
    GROUP BY c.sector_code
    """
)


def snapshot(
    conn: Connection,
    district: str,
    week: date,
    model: CoverageModel,
    origin: Origin,
    source: str,
) -> int:
    """Write one coverage_snapshot row per sector for the week. Returns rows written."""
    points, _ = demand_points(conn, district)
    state = cover(model, seats(conn, district, week), points)
    children: dict[str, float] = defaultdict(float)
    uncovered: dict[str, float] = defaultdict(float)
    for point in points:
        children[point.area_code] += point.children
        uncovered[point.area_code] += state.uncovered(point.id)
    crowded: dict[str, int] = {
        row.sector_code: row.n
        for row in conn.execute(OVERCROWDED, {"district": district, "week": week})
    }
    rows = [
        {
            "area_code": area,
            "week_start": week,
            "model_version_id": model.version,
            "children_covered": round(children[area] - uncovered[area]),
            "children_uncovered": round(uncovered[area]),
            "overcrowded_centres": crowded.get(area, 0),
            "catchment_minutes": model.catchment_minutes,
            "source": source,
            "reference_year": week.year,
            "origin": origin,
        }
        for area in sorted(children)
    ]
    conn.execute(insert(CoverageSnapshot), rows)
    return len(rows)
