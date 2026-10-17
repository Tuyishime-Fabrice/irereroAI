from sqlalchemy import Connection, text

from irerero_engine.coverage import Minutes

QUERY = text(
    """
    SELECT k.seat_id, k.cell_id, k.walk_minutes
    FROM catchment k JOIN population_cell c ON c.id = k.cell_id
    JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district
    """
)


def walking_minutes(conn: Connection, district: str) -> Minutes:
    """Precomputed walking minutes from every centre and candidate site to nearby cells."""
    out: dict[str, dict[str, float]] = {}
    for seat, cell, minutes in conn.execute(QUERY, {"district": district}):
        out.setdefault(seat, {})[cell] = minutes
    return out
