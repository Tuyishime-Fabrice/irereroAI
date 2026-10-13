"""Run early warning and keep one alert per ongoing problem.

An alert opens the first week a rule fires. While the problem continues, the same alert is
updated with the latest numbers and severity; it closes only when a person resolves it.
"""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Connection, insert, select, update

from irerero_api.engine_io.centres import histories
from irerero_contract.enums import AlertStatus, Origin
from irerero_contract.tables import Alert
from irerero_engine.early_warning import EarlyWarning, Signal


def _open_alert(conn: Connection, signal: Signal) -> uuid.UUID | None:
    return conn.execute(
        select(Alert.id)
        .where(
            Alert.centre_code == signal.centre_code,
            Alert.kind == signal.kind,
            Alert.status != AlertStatus.RESOLVED,
        )
        .order_by(Alert.week_start.desc())
        .limit(1)
    ).scalar_one_or_none()


def refresh_alerts(
    conn: Connection,
    centre_codes: Sequence[str],
    weeks: Sequence[date],
    warning: EarlyWarning,
    origin: Origin,
) -> list[Signal]:
    """Check centres as of the last week in `weeks`. Returns the signals that fired."""
    fired: list[Signal] = []
    for history in histories(conn, centre_codes):
        for signal in warning.check(history, weeks):
            fired.append(signal)
            values = {
                "severity": signal.severity,
                "reason_en": signal.reason_en,
                "reason_rw": signal.reason_rw,
                "evidence": dict(signal.evidence),
                "rule": signal.rule,
                "model_version_id": warning.version,
            }
            existing = _open_alert(conn, signal)
            if existing is None:
                conn.execute(
                    insert(Alert).values(
                        centre_code=signal.centre_code,
                        week_start=signal.week_start,
                        kind=signal.kind,
                        origin=origin,
                        **values,
                    )
                )
            else:
                conn.execute(update(Alert).where(Alert.id == existing).values(**values))
    return fired
