from collections.abc import Sequence
from datetime import date

from sqlalchemy import Connection, text

from irerero_engine.coverage import Seat
from irerero_engine.early_warning import CentreHistory, WeekReport
from irerero_engine.types import Position

SEATS = text(
    """
    SELECT c.code, c.capacity, c.serves_0_2,
        ST_X(ST_Transform(c.location, 32735)) AS x, ST_Y(ST_Transform(c.location, 32735)) AS y,
        (SELECT r.days_open FROM weekly_report r WHERE r.centre_code = c.code
            AND r.week_start <= :week ORDER BY r.week_start DESC LIMIT 1) AS days_open
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :district AND c.status = 'active'
    ORDER BY c.code
    """
)

HISTORY = text(
    """
    SELECT c.code, c.name, c.capacity, r.week_start,
        r.enrolled_0_2_female + r.enrolled_0_2_male + r.enrolled_3_6_female
            + r.enrolled_3_6_male AS enrolled,
        r.avg_daily_attendance, r.waiting_list, r.days_open, r.wash_available, r.main_problem
    FROM centre c LEFT JOIN weekly_report r ON r.centre_code = c.code
    WHERE c.code = ANY(:codes)
    ORDER BY c.code, r.week_start
    """
)


def seats(conn: Connection, district: str, week: date) -> list[Seat]:
    """Places offered by active centres; a centre that reported zero open days offers none."""
    return [
        Seat(
            row.code,
            Position(row.x, row.y),
            0 if row.days_open == 0 else row.capacity,
            serves_0_2=row.serves_0_2,
        )
        for row in conn.execute(SEATS, {"district": district, "week": week})
    ]


def centre_codes(conn: Connection, district: str) -> list[str]:
    return list(
        conn.execute(
            text(
                "SELECT c.code FROM centre c JOIN admin_unit s ON s.code = c.sector_code "
                "WHERE s.parent_code = :d ORDER BY c.code"
            ),
            {"d": district},
        ).scalars()
    )


def histories(conn: Connection, codes: Sequence[str]) -> list[CentreHistory]:
    grouped: dict[str, tuple[str, int, list[WeekReport]]] = {}
    for row in conn.execute(HISTORY, {"codes": list(codes)}):
        entry = grouped.setdefault(row.code, (row.name, row.capacity, []))
        if row.week_start is not None:
            entry[2].append(
                WeekReport(
                    row.week_start,
                    row.enrolled,
                    row.avg_daily_attendance,
                    row.waiting_list,
                    row.days_open,
                    row.wash_available,
                    row.main_problem,
                )
            )
    return [
        CentreHistory(code, name, capacity, tuple(reports))
        for code, (name, capacity, reports) in grouped.items()
    ]
