"""Run the engine baselines over the seeded weeks, as if reports had arrived week by week.

This produces the alert history and weekly coverage the week scrubber replays.
"""

from sqlalchemy import Connection, insert

from irerero_api.engine_io.centres import centre_codes
from irerero_api.services.alerts import refresh_alerts
from irerero_api.services.coverage import snapshot
from irerero_api.services.reliability import refresh_reliability
from irerero_contract.enums import Origin
from irerero_contract.tables import ModelVersion
from irerero_engine.coverage import StraightLineCoverage
from irerero_engine.early_warning import RuleBasedEarlyWarning
from irerero_engine.versions import BASELINES
from pipelines.demo.config import DEMO_DISTRICT, WEEKS

SOURCE = "IrereroAI engine baselines over simulated reports"


def load_model_versions(conn: Connection) -> None:
    conn.execute(insert(ModelVersion), [dict(b) | {"metrics": {}} for b in BASELINES])


def derive(conn: Connection) -> dict[str, int]:
    codes = centre_codes(conn, DEMO_DISTRICT)
    warning = RuleBasedEarlyWarning()
    model = StraightLineCoverage()
    snapshots = 0
    for week_index in range(len(WEEKS)):
        weeks_so_far = WEEKS[: week_index + 1]
        refresh_alerts(conn, codes, weeks_so_far, warning, Origin.SIMULATED)
        snapshots += snapshot(
            conn, DEMO_DISTRICT, weeks_so_far[-1], model, Origin.SIMULATED, SOURCE
        )
    refresh_reliability(conn, codes, WEEKS)
    return {"coverage_snapshot": snapshots}
