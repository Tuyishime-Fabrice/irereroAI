from sqlalchemy import Connection, text

from irerero_engine.coverage import Seat
from irerero_engine.types import Position

SEATS = text(
    """
    SELECT c.code, c.capacity, c.serves_0_2,
        ST_X(ST_Transform(c.location, 32735)) AS x, ST_Y(ST_Transform(c.location, 32735)) AS y
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district AND c.status = 'active'
    ORDER BY c.code
    """
)


def seats(conn: Connection, district: str) -> list[Seat]:
    """Places offered by the district's active centres."""
    return [
        Seat(row.code, Position(row.x, row.y), row.capacity, serves_0_2=row.serves_0_2)
        for row in conn.execute(SEATS, {"district": district})
    ]
