from collections.abc import Sequence

from sqlalchemy import Connection, text

from irerero_engine.coverage import DemandPoint
from irerero_engine.types import Position

# Where children live inside each sector: precomputed 500 m cells, from WorldPop when loaded,
# otherwise an even spread over the sector's area.
QUERY = text(
    """
    SELECT c.id, c.sector_code AS code, ST_X(ST_Transform(c.location, 32735)) AS x,
        ST_Y(ST_Transform(c.location, 32735)) AS y, c.share
    FROM population_cell c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district
    ORDER BY c.id
    """
)

BOUNDS = text(
    """
    SELECT DISTINCT ON (area_code) area_code,
        children_0_2_estimate + children_3_6_estimate AS estimate,
        children_0_2_low + children_3_6_low AS low,
        children_0_2_high + children_3_6_high AS high,
        children_0_2_estimate AS young, children_3_6_estimate AS old,
        stunting_risk_estimate AS risk, stunting_risk_low AS risk_low,
        stunting_risk_high AS risk_high, mothers_barrier_share_estimate AS barrier,
        mothers_barrier_share_low AS barrier_low, mothers_barrier_share_high AS barrier_high
    FROM need_estimate WHERE area_code = ANY(:codes)
    ORDER BY area_code, reference_year DESC
    """
)


def demand_points(
    conn: Connection, district: str
) -> tuple[list[DemandPoint], dict[str, tuple[float, float]]]:
    """Cells with children, and per-sector (low/estimate, high/estimate) child counts."""
    cells = conn.execute(QUERY, {"district": district}).all()
    codes: Sequence[str] = sorted({c.code for c in cells})
    need = {r.area_code: r for r in conn.execute(BOUNDS, {"codes": list(codes)})}
    points = []
    for cell in cells:
        area = need.get(cell.code)
        if area is None:
            continue
        points.append(
            DemandPoint(
                id=cell.id,
                position=Position(cell.x, cell.y),
                area_code=cell.code,
                children_0_2=area.young * cell.share,
                children_3_6=area.old * cell.share,
                stunting_risk=area.risk,
                mothers_barrier_share=area.barrier,
                stunting_risk_bounds=(area.risk_low, area.risk_high),
                mothers_barrier_bounds=(area.barrier_low, area.barrier_high),
            )
        )
    bounds = {
        code: (row.low / row.estimate, row.high / row.estimate)
        for code, row in need.items()
        if row.estimate
    }
    return points, bounds
