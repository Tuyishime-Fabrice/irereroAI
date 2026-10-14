"""Precompute coverage for every catchment step from the loaded centres and need."""

from sqlalchemy import Connection, insert

from irerero_api.services.coverage import snapshot
from irerero_contract.enums import Origin
from irerero_contract.tables import ModelVersion
from irerero_engine.coverage import DEFAULT_METRES_PER_MINUTE
from irerero_engine.versions import BASELINES
from pipelines.demo.config import DEMO_DISTRICT, REFERENCE_YEAR

SOURCE = "IrereroAI coverage baseline over simulated centres"


def load_model_versions(conn: Connection) -> None:
    conn.execute(insert(ModelVersion), [dict(b) | {"metrics": {}} for b in BASELINES])


def derive(conn: Connection) -> dict[str, int]:
    rows = snapshot(
        conn, DEMO_DISTRICT, DEFAULT_METRES_PER_MINUTE, Origin.SIMULATED, SOURCE, REFERENCE_YEAR
    )
    return {"coverage_snapshot": rows}
