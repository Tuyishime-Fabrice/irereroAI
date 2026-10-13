from collections.abc import Sequence

from sqlalchemy import Connection, text

from irerero_engine.coverage import DemandPoint
from irerero_engine.types import Position

# Children are spread over a 1 km grid in proportion to area. Phase 2 replaces the uniform
# spread with WorldPop densities without changing the engine.
CELL_METRES = 1000

QUERY = text(
    """
    WITH sector AS (
        SELECT a.code, ST_Transform(a.geom, 32735) AS g
        FROM admin_unit a WHERE a.parent_code = :district AND a.level = 'sector'
    ), cell AS (
        SELECT s.code, s.g, grid.i, grid.j, ST_Intersection(grid.geom, s.g) AS part
        FROM sector s, ST_SquareGrid(:size, s.g) AS grid
        WHERE ST_Intersects(grid.geom, s.g)
    )
    SELECT code, i, j, ST_X(ST_PointOnSurface(part)) AS x, ST_Y(ST_PointOnSurface(part)) AS y,
        ST_Area(part) / ST_Area(g) AS share
    FROM cell WHERE NOT ST_IsEmpty(part) AND ST_Area(part) > 0
    ORDER BY code, i, j
    """
)

BOUNDS = text(
    """
    SELECT DISTINCT ON (area_code) area_code,
        children_0_2_estimate + children_3_6_estimate AS estimate,
        children_0_2_low + children_3_6_low AS low,
        children_0_2_high + children_3_6_high AS high,
        children_0_2_estimate AS young, children_3_6_estimate AS old,
        stunting_risk_estimate AS risk, mothers_barrier_share_estimate AS barrier
    FROM need_estimate WHERE area_code = ANY(:codes)
    ORDER BY area_code, reference_year DESC
    """
)


def demand_points(
    conn: Connection, district: str
) -> tuple[list[DemandPoint], dict[str, tuple[float, float]]]:
    """Grid points with children, and per-sector (low/estimate, high/estimate) child counts."""
    cells = conn.execute(QUERY, {"district": district, "size": CELL_METRES}).all()
    codes: Sequence[str] = sorted({c.code for c in cells})
    need = {r.area_code: r for r in conn.execute(BOUNDS, {"codes": list(codes)})}
    points = []
    for cell in cells:
        area = need.get(cell.code)
        if area is None:
            continue
        points.append(
            DemandPoint(
                id=f"{cell.code}:{cell.i}:{cell.j}",
                position=Position(cell.x, cell.y),
                area_code=cell.code,
                children_0_2=area.young * cell.share,
                children_3_6=area.old * cell.share,
                stunting_risk=area.risk,
                mothers_barrier_share=area.barrier,
            )
        )
    bounds = {
        code: (row.low / row.estimate, row.high / row.estimate)
        for code, row in need.items()
        if row.estimate
    }
    return points, bounds
