"""The engine baselines against the seeded demo: the checks the demo story depends on."""

import uuid

from sqlalchemy import Engine, insert, text

from irerero_api.services.planning import planning_input
from irerero_contract.tables import Decision, Recommendation, Scenario
from irerero_engine.coverage import StraightLineCoverage
from irerero_engine.optimizer import GreedyOptimizer, Weights, largest_population_first
from pipelines.demo.accounts import account_id
from pipelines.demo.config import CURRENT_WEEK, DEMO_DISTRICT
from pipelines.demo.story import STORY_BY_ROLE

BUDGET = 120_000_000
WEIGHTS = Weights(stunting=0.4, readiness=0.4, jobs=0.2)
MODEL = StraightLineCoverage()


def test_early_warning_flags_each_planted_problem_and_nothing_else(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        alerts = {
            (r.centre_code, r.kind)
            for r in conn.execute(text("SELECT centre_code, kind FROM alert"))
        }
    expected = {
        (STORY_BY_ROLE["no_water"].code, "attendance_drop"),
        (STORY_BY_ROLE["no_water"].code, "wash"),
        (STORY_BY_ROLE["overcrowded"].code, "overcrowding"),
        (STORY_BY_ROLE["stopped_reporting"].code, "missing_report"),
    }
    assert alerts == expected


def test_optimizer_respects_budget_and_beats_population_baseline(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        data = planning_input(conn, DEMO_DISTRICT, CURRENT_WEEK, BUDGET, WEIGHTS, MODEL)
    plan = GreedyOptimizer(MODEL).plan(data)
    baseline = largest_population_first(MODEL, data)
    assert plan.outcomes.cost <= BUDGET
    assert plan.outcomes.children_reached.estimate > baseline.outcomes.children_reached.estimate
    assert plan.outcomes.high_risk_reached > baseline.outcomes.high_risk_reached


def test_support_goes_to_centres_with_problems(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        data = planning_input(conn, DEMO_DISTRICT, CURRENT_WEEK, BUDGET, WEIGHTS, MODEL)
    supported = {
        s.candidate.centre_code
        for s in GreedyOptimizer(MODEL).plan(data).suggestions
        if s.candidate.action == "support"
    }
    assert STORY_BY_ROLE["no_water"].code in supported
    assert STORY_BY_ROLE["caregiver_home"].code not in supported


def test_rejection_with_no_land_removes_the_site_from_the_next_run(demo_engine: Engine) -> None:
    with demo_engine.begin() as conn:
        data = planning_input(conn, DEMO_DISTRICT, CURRENT_WEEK, BUDGET, WEIGHTS, MODEL)
        top = GreedyOptimizer(MODEL).plan(data).suggestions[0]
        scenario_id, recommendation_id = uuid.uuid4(), uuid.uuid4()
        conn.execute(
            insert(Scenario).values(
                id=scenario_id,
                district_code=DEMO_DISTRICT,
                name="test",
                budget_rwf=BUDGET,
                weight_stunting=0.4,
                weight_readiness=0.4,
                weight_jobs=0.2,
                constraints={},
                model_version_id=GreedyOptimizer.version,
                origin="simulated",
                created_by=account_id("district_planner"),
            )
        )
        conn.execute(
            insert(Recommendation).values(
                id=recommendation_id,
                scenario_id=scenario_id,
                rank=1,
                action=top.candidate.action.value,
                site_id=top.candidate.id,
                children_reached=0,
                reached_low=0,
                reached_high=0,
                high_risk_children_reached=0,
                mothers_under3_reached=0,
                cost_rwf=0,
                score=0,
                drivers=[],
                sources=[],
            )
        )
        conn.execute(
            insert(Decision).values(
                recommendation_id=recommendation_id,
                user_id=account_id("district_planner"),
                verdict="reject",
                reason_code="no_land",
            )
        )
        rerun = planning_input(conn, DEMO_DISTRICT, CURRENT_WEEK, BUDGET, WEIGHTS, MODEL)
        assert top.candidate.id in rerun.constraints.excluded
        ids = {s.candidate.id for s in GreedyOptimizer(MODEL).plan(rerun).suggestions}
        assert top.candidate.id not in ids
        conn.rollback()
