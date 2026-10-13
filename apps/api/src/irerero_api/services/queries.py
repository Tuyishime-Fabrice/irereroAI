"""Read queries shared by several routes."""

from datetime import date
from typing import Any

from sqlalchemy import Row, text
from sqlalchemy.orm import Session

CENTRE_ROWS = text(
    """
    SELECT c.*, s.name AS sector_name, s.parent_code AS district_code,
        ST_X(c.location) AS lon, ST_Y(c.location) AS lat,
        last.week_start AS last_report_week,
        last.enrolled AS latest_enrolled, last.avg_daily_attendance AS latest_attendance,
        (last.week_start = :week) AS reported_this_week,
        (SELECT count(*) FROM alert a WHERE a.centre_code = c.code AND a.status <> 'resolved')
            AS open_alerts
    FROM centre c
    JOIN admin_unit s ON s.code = c.sector_code
    LEFT JOIN LATERAL (
        SELECT r.week_start, r.avg_daily_attendance, r.enrolled_0_2_female + r.enrolled_0_2_male
            + r.enrolled_3_6_female + r.enrolled_3_6_male AS enrolled
        FROM weekly_report r WHERE r.centre_code = c.code AND r.week_start <= :week
        ORDER BY r.week_start DESC LIMIT 1
    ) last ON true
    WHERE (CAST(:area AS text) IS NULL OR c.sector_code = :area OR s.parent_code = :area
           OR :area = 'RW')
      AND (CAST(:code AS text) IS NULL OR c.code = :code)
    ORDER BY c.sector_code, c.code
    """
)

ALERT_ROWS = text(
    """
    SELECT a.*, c.name AS centre_name, c.capacity, s.code AS sector_code, s.name AS sector_name,
        u.display_name AS assigned_name
    FROM alert a
    JOIN centre c ON c.code = a.centre_code
    JOIN admin_unit s ON s.code = c.sector_code
    LEFT JOIN user_account u ON u.id = a.assigned_to
    WHERE (CAST(:area AS text) IS NULL OR s.code = :area OR s.parent_code = :area OR :area = 'RW')
      AND (CAST(:centre AS text) IS NULL OR a.centre_code = :centre)
      AND (CAST(:id AS uuid) IS NULL OR a.id = :id)
      AND a.week_start <= :as_of
    ORDER BY CASE a.status WHEN 'open' THEN 0 WHEN 'acknowledged' THEN 1 ELSE 2 END,
        CASE a.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, a.week_start
    """
)


def centre_rows(
    session: Session, week: date, area: str | None = None, code: str | None = None
) -> list[Row[Any]]:
    return list(session.execute(CENTRE_ROWS, {"week": week, "area": area, "code": code}).all())


def alert_rows(
    session: Session,
    as_of: date,
    area: str | None = None,
    centre: str | None = None,
    alert_id: object = None,
) -> list[Row[Any]]:
    return list(
        session.execute(
            ALERT_ROWS, {"as_of": as_of, "area": area, "centre": centre, "id": alert_id}
        ).all()
    )
