"""Build the database: real files where they are present, demo data where they are not.

    python -m pipelines.build

Put dataset files in data/raw/<dataset>/ (see DATA_SOURCES.md). Each file found is checked
against its columns and loaded with its checksum and checks on record; anything missing is
stood in for by the current demo data, stored with origin = simulated so the app labels it.
Then catchments, coverage and need are precomputed so the planner's screens answer instantly.

Deterministic: the same files give the same database. The database is rebuilt from scratch,
so the build refuses to run where official or partner data was entered outside it.
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from irerero_api.services.coverage import snapshot
from irerero_contract.enums import Origin, RunStatus
from irerero_contract.tables import ModelVersion
from irerero_engine.travel import StraightLineTravel, TravelTimes
from irerero_engine.versions import BASELINES
from pipelines.config import PILOT_DISTRICTS
from pipelines.db import engine as make_engine
from pipelines.demo.accounts import load_accounts
from pipelines.demo.catalogue import load_catalogue, load_need_model, load_planning_defaults
from pipelines.demo.centres import load_centres
from pipelines.demo.config import REFERENCE_YEAR
from pipelines.demo.demand import load_demand
from pipelines.demo.need import load_need
from pipelines.demo.planning import load_sites, load_unit_costs
from pipelines.need_model import apply_loaded_need
from pipelines.precompute import even_population_cells, nearest_centre_minutes, walking_catchments
from pipelines.runs import RAW_DIR, REPO_ROOT, CheckResult, RunRecorder, file_fingerprint
from pipelines.sources import LOADERS
from pipelines.sources.base import Loader
from pipelines.sources.boundaries import OFFICIAL as BOUNDARIES
from pipelines.sources.boundaries import BoundaryDownloadError, load_boundaries
from pipelines.sources.osm import Osm, pilot_bbox, read_extract, road_network
from pipelines.sources.readers import SchemaError

ALEMBIC_INI = REPO_ROOT / "apps" / "api" / "alembic.ini"
COVERAGE_SOURCE = "IrereroAI walking-time coverage"


class RealDataPresentError(RuntimeError):
    pass


def guard(engine: Engine) -> None:
    """Never wipe a database holding official or partner data that this build did not load."""
    if not inspect(engine).has_table("pipeline_run"):
        return
    with engine.connect() as conn:
        outside = conn.execute(
            text(
                "SELECT count(*) FROM pipeline_run WHERE origin IN ('official', 'partner') "
                "AND NOT (pipeline = ANY(:ours))"
            ),
            {"ours": [*(loader.dataset.key for loader in LOADERS), "boundaries"]},
        ).scalar_one()
    if outside:
        raise RealDataPresentError(
            "This database holds official or partner data loaded outside the build; "
            "the build will not reset it."
        )


def reset(engine: Engine) -> None:
    """Drop every table, then migrate from scratch. PostGIS's own tables stay."""
    with engine.begin() as conn:
        tables = conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename <> 'spatial_ref_sys'"
            )
        ).scalars()
        for table in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        conn.execute(text("DROP FUNCTION IF EXISTS audit_log_append_only() CASCADE"))
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(Path(ALEMBIC_INI).parent / "alembic"))
    command.upgrade(config, "head")


def run_loader(engine: Engine, loader: Loader, raw: Path) -> dict[str, int]:
    folder = loader.folder(raw)
    files = [folder / f.name for f in loader.dataset.files if (folder / f.name).is_file()]
    recorder = RunRecorder(engine, loader.dataset.key, loader.dataset.origin)
    run_id = recorder.start([file_fingerprint(p) for p in files])
    try:
        with engine.begin() as conn:
            report = loader.load(conn, folder, run_id)
    except SchemaError as error:
        recorder.finish(RunStatus.FAILED, {}, [CheckResult("schema", False, str(error))])
        raise
    except Exception:
        recorder.finish(RunStatus.FAILED, {}, [])
        raise
    recorder.finish(RunStatus.SUCCEEDED, report.rows, report.checks)
    return report.rows


def travel_times(engine: Engine, raw: Path) -> TravelTimes:
    """Along roads and paths with the OSM extract; otherwise estimated in a straight line."""
    if not Osm.dataset.present(raw):
        return StraightLineTravel()
    with engine.begin() as conn:
        extract = read_extract(
            raw / "osm" / Osm.dataset.files[0].name, pilot_bbox(conn, PILOT_DISTRICTS)
        )
        return road_network(conn, extract, StraightLineTravel().metres_per_minute)


def build(engine: Engine, raw: Path = RAW_DIR) -> dict[str, int]:
    guard(engine)
    reset(engine)
    present = {
        d.key for d in (BOUNDARIES, *(loader.dataset for loader in LOADERS)) if d.present(raw)
    }
    counts: dict[str, int] = {}
    counts["admin_unit"], _ = load_boundaries(engine, raw)

    # The demo data stands in for whatever is missing, labelled simulated.
    demo = RunRecorder(engine, "demo_generator", Origin.SIMULATED)
    run_id = demo.start([])
    try:
        with engine.begin() as conn:
            counts["data_source"] = load_catalogue(conn, present)
            load_need_model(conn)
            conn.execute(
                ModelVersion.__table__.insert(), [dict(b) | {"metrics": {}} for b in BASELINES]
            )
            load_planning_defaults(conn)
            counts["user_account"] = load_accounts(conn)
            counts["need_estimate"] = load_need(conn, run_id)
            if "ecd_centres" not in present:
                counts["centre"] = len(load_centres(conn, run_id))
            counts["unit_cost"] = load_unit_costs(conn, run_id)
    except Exception:
        demo.finish(RunStatus.FAILED, {}, [])
        raise
    demo.finish(
        RunStatus.SUCCEEDED,
        dict(counts),
        [CheckResult("origin_simulated", True, "every generated row has origin=simulated")],
    )

    for loader in LOADERS:
        if loader.dataset.key in present:
            for table, rows in run_loader(engine, loader, raw).items():
                counts[table] = counts.get(table, 0) + rows

    travel = travel_times(engine, raw)
    with engine.begin() as conn:
        counts["candidate_site"] = load_sites(conn, run_id)
        counts["demand_signal"] = load_demand(conn)
        counts["need_estimate_official"] = apply_loaded_need(conn)
        if "worldpop" not in present:
            counts["population_cell"] = even_population_cells(conn, PILOT_DISTRICTS)
        counts["catchment"] = walking_catchments(conn, PILOT_DISTRICTS, travel)
        nearest_centre_minutes(conn, PILOT_DISTRICTS, travel)
        # Coverage counts children against centres: real only when both are loaded.
        origin = Origin.PARTNER if {"ecd_centres", "census_2022"} <= present else Origin.SIMULATED
        counts["coverage_snapshot"] = sum(
            snapshot(conn, district, origin, COVERAGE_SOURCE, REFERENCE_YEAR)
            for district in PILOT_DISTRICTS
        )
    # Fresh tables have no statistics; without them the planner's queries take seconds.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ANALYZE"))
    return counts


def main() -> int:
    try:
        counts = build(make_engine())
    except (BoundaryDownloadError, RealDataPresentError, SchemaError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for table, rows in counts.items():
        print(f"{table:24} {rows:7}")
    print("Missing datasets were stood in for by demo data, labelled origin=simulated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
