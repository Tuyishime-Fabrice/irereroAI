from collections.abc import Sequence
from datetime import date

from sqlalchemy import Connection, text, update

from irerero_contract.tables import Centre
from irerero_engine.early_warning import reliability


def refresh_reliability(
    conn: Connection, centre_codes: Sequence[str], weeks: Sequence[date]
) -> None:
    rows = conn.execute(
        text(
            "SELECT centre_code, week_start, cardinality(quality_flags) > 0 AS flagged "
            "FROM weekly_report WHERE centre_code = ANY(:codes) AND week_start = ANY(:weeks)"
        ),
        {"codes": list(centre_codes), "weeks": list(weeks)},
    ).all()
    by_centre: dict[str, list[tuple[date, bool]]] = {code: [] for code in centre_codes}
    for code, week, flagged in rows:
        by_centre[code].append((week, flagged))
    for code, reports in by_centre.items():
        conn.execute(
            update(Centre)
            .where(Centre.code == code)
            .values(reliability_score=reliability(reports, weeks))
        )
