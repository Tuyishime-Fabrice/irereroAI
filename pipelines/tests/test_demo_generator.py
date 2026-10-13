from sqlalchemy import Engine, text

from pipelines.demo.generate import generate
from pipelines.demo.story import STORY_BY_ROLE

FINGERPRINT_TABLES = ("centre", "weekly_report", "need_estimate", "candidate_site", "demand_signal")


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
    generate(demo_engine)
    _strip_run_ids(demo_engine)
    first = _fingerprint(demo_engine)
    generate(demo_engine)
    _strip_run_ids(demo_engine)
    assert _fingerprint(demo_engine) == first
    generate(demo_engine)


def test_everything_generated_is_labelled_simulated(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        for table in ("centre", "weekly_report", "need_estimate", "candidate_site", "unit_cost"):
            origins = conn.execute(text(f"SELECT DISTINCT origin FROM {table}")).scalars().all()  # noqa: S608
            assert origins == ["simulated"], table
        boundaries = conn.execute(text("SELECT DISTINCT origin FROM admin_unit")).scalars().all()
        assert boundaries == ["public"]


def test_planted_problems_are_present(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        weeks = dict(
            conn.execute(
                text("SELECT centre_code, count(*) FROM weekly_report GROUP BY centre_code")
            ).all()
        )
        assert weeks[STORY_BY_ROLE["stopped_reporting"].code] == 9
        assert weeks[STORY_BY_ROLE["caregiver_home"].code] == 11

        no_water = conn.execute(
            text(
                "SELECT count(*) FROM weekly_report WHERE centre_code = :c "
                "AND main_problem = 'no_water' AND NOT wash_available"
            ),
            {"c": STORY_BY_ROLE["no_water"].code},
        ).scalar_one()
        assert no_water == 3

        jump_flags = conn.execute(
            text(
                "SELECT count(*) FROM weekly_report WHERE centre_code = :c "
                "AND 'enrolment_jump' = ANY(quality_flags)"
            ),
            {"c": STORY_BY_ROLE["implausible_jump"].code},
        ).scalar_one()
        assert jump_flags == 1

        crowded = conn.execute(
            text(
                "SELECT bool_and(r.avg_daily_attendance > c.capacity) FROM weekly_report r "
                "JOIN centre c ON c.code = r.centre_code WHERE c.code = :c"
            ),
            {"c": STORY_BY_ROLE["overcrowded"].code},
        ).scalar_one()
        assert crowded


def test_demand_clusters_in_the_underserved_sector(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        by_sector = dict(
            conn.execute(
                text("SELECT sector_code, count(*) FROM demand_signal GROUP BY sector_code")
            ).all()
        )
    assert (
        max(by_sector, key=lambda code: by_sector[code]) == STORY_BY_ROLE["underserved"].sector_code
    )


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
