"""Build the demo database: real boundaries plus clearly labelled simulated data for Gicumbi.

    python -m pipelines.demo.generate

Deterministic and idempotent: the database is reset and rebuilt from the same seed every time.
It refuses to run on a database holding official or partner data.
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from irerero_contract.enums import Origin, RunStatus
from pipelines.adapter import REPO_ROOT, CheckResult, RunRecorder
from pipelines.db import engine as make_engine
from pipelines.demo.accounts import CAREGIVER_CENTRE, account_id, load_accounts
from pipelines.demo.catalogue import load_catalogue, load_need_model
from pipelines.demo.centres import load_centres
from pipelines.demo.demand import load_demand
from pipelines.demo.geography import BoundaryDownloadError, load_boundaries
from pipelines.demo.need import load_need
from pipelines.demo.planning import load_sites, load_unit_costs
from pipelines.demo.reports import load_reports

ALEMBIC_INI = REPO_ROOT / "apps" / "api" / "alembic.ini"


class RealDataPresentError(RuntimeError):
    pass


def guard(engine: Engine) -> None:
    """Never wipe a database that holds official or partner data."""
    if not inspect(engine).has_table("pipeline_run"):
        return
    with engine.connect() as conn:
        real = conn.execute(
            text("SELECT count(*) FROM pipeline_run WHERE origin IN ('official', 'partner')")
        ).scalar_one()
    if real:
        raise RealDataPresentError(
            "This database holds official or partner data; the demo generator will not reset it."
        )


def reset(engine: Engine) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(Path(ALEMBIC_INI).parent / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def generate(engine: Engine) -> dict[str, int]:
    guard(engine)
    reset(engine)
    counts = {"admin_unit": load_boundaries(engine)}
    recorder = RunRecorder(engine, "demo_generator", Origin.SIMULATED)
    run_id = recorder.start([])
    try:
        with engine.begin() as conn:
            counts["data_source"] = load_catalogue(conn)
            load_need_model(conn)
            counts["user_account"] = load_accounts(conn)
            centres = load_centres(conn, run_id)
            counts["centre"] = len(centres)
            submitters = {CAREGIVER_CENTRE: account_id("caregiver")}
            counts["weekly_report"] = load_reports(conn, run_id, centres, submitters)
            counts["need_estimate"] = load_need(conn, run_id)
            counts["unit_cost"] = load_unit_costs(conn, run_id)
            counts["candidate_site"] = load_sites(conn, run_id, centres)
            counts["demand_signal"] = load_demand(conn)
    except Exception:
        recorder.finish(RunStatus.FAILED, {}, [])
        raise
    checks = [CheckResult("origin_simulated", True, "every generated row has origin=simulated")]
    recorder.finish(RunStatus.SUCCEEDED, counts, checks)
    return counts


def main() -> int:
    try:
        counts = generate(make_engine())
    except (BoundaryDownloadError, RealDataPresentError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for table, rows in counts.items():
        print(f"{table:16} {rows:6}")
    print("Demo data is simulated and labelled origin=simulated, except boundaries (public).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
