from sqlalchemy import Engine, text

from irerero_engine.coverage import CATCHMENT_STEPS
from pipelines.build import build
from pipelines.demo.story import STORY_CENTRES
from pipelines.sources.__main__ import DOC, document

FINGERPRINT_TABLES = (
    "centre",
    "need_estimate",
    "candidate_site",
    "demand_signal",
)
STORY = {c.role: c for c in STORY_CENTRES}


def _fingerprint(engine: Engine) -> dict[str, str]:
    with engine.connect() as conn:
        return {
            table: conn.execute(
                text(
                    f"SELECT md5(string_agg(t::text, '|' ORDER BY t::text)) FROM "  # noqa: S608
                    f"(SELECT * FROM {table}) t"
                )
            ).scalar_one()
            for table in FINGERPRINT_TABLES
        }


def _strip_run_ids(engine: Engine) -> None:
    with engine.begin() as conn:
        for table in FINGERPRINT_TABLES:
            if table != "demand_signal":
                conn.execute(text(f"UPDATE {table} SET pipeline_run_id = NULL"))  # noqa: S608


def test_generator_is_deterministic(demo_engine: Engine) -> None:
    build(demo_engine)
    _strip_run_ids(demo_engine)
    first = _fingerprint(demo_engine)
    build(demo_engine)
    _strip_run_ids(demo_engine)
    assert _fingerprint(demo_engine) == first
    build(demo_engine)


def test_everything_generated_is_labelled_simulated(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        for table in (
            "centre",
            "need_estimate",
            "candidate_site",
            "unit_cost",
            "demand_signal",
            "coverage_snapshot",
        ):
            origins = conn.execute(text(f"SELECT DISTINCT origin FROM {table}")).scalars().all()  # noqa: S608
            assert origins == ["simulated"], table
        boundaries = conn.execute(text("SELECT DISTINCT origin FROM admin_unit")).scalars().all()
        assert boundaries == ["public"]


def test_planted_centres_are_present(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        rows = {
            r.code: r
            for r in conn.execute(
                text("SELECT code, type, capacity, enrolment, water_available FROM centre")
            )
        }
    assert not rows[STORY["no_water"].code].water_available
    crowded = rows[STORY["overcrowded"].code]
    assert crowded.enrolment > crowded.capacity
    home = rows[STORY["outgrown_home"].code]
    assert home.type == "home_based" and home.enrolment > home.capacity


def test_coverage_is_precomputed_for_every_catchment_step(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        uncovered = dict(
            conn.execute(
                text(
                    "SELECT catchment_minutes, sum(children_uncovered) FROM coverage_snapshot "
                    "GROUP BY catchment_minutes ORDER BY catchment_minutes"
                )
            ).all()
        )
    assert sorted(uncovered) == list(CATCHMENT_STEPS)
    totals = [uncovered[step] for step in CATCHMENT_STEPS]
    assert totals == sorted(totals, reverse=True)


def test_demand_clusters_in_the_underserved_sector(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        by_sector = dict(
            conn.execute(
                text("SELECT sector_code, count(*) FROM demand_signal GROUP BY sector_code")
            ).all()
        )
    assert max(by_sector, key=lambda code: by_sector[code]) == STORY["underserved"].sector_code


def test_demand_signals_store_only_grid_cells(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        off_grid = conn.execute(
            text(
                "SELECT count(*) FROM demand_signal WHERE "
                "(ST_X(ST_Transform(cell_centre, 32735))::numeric - 250) % 500 > 0.01"
            )
        ).scalar_one()
    assert off_grid == 0


def test_gicumbi_stunting_matches_the_anchor(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        weighted = conn.execute(
            text(
                "SELECT sum(stunting_risk_estimate * (children_0_2_estimate + "
                "children_3_6_estimate)) / sum(children_0_2_estimate + children_3_6_estimate) "
                "FROM need_estimate n JOIN admin_unit a ON a.code = n.area_code "
                "WHERE a.parent_code = 'D-GICUMBI'"
            )
        ).scalar_one()
    assert abs(weighted - 0.388) < 0.002


def test_data_sources_document_is_current() -> None:
    assert DOC.read_text() == document(), "run python -m pipelines.sources --write"


def test_the_catalogue_marks_simulated_stand_ins(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        status = dict(conn.execute(text("SELECT id, status FROM data_source")).all())
    assert status["census_2022"] == "simulated_stand_in"
    assert status["ecd_centres"] == "simulated_stand_in"
    assert status["worldpop"] == "planned"
    assert status["geoboundaries"] == "loaded"
