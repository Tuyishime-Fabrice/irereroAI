from irerero_engine.coverage import initial_state
from irerero_engine.optimizer import (
    Constraints,
    GreedyOptimizer,
    PlanningInput,
    Weights,
    largest_population_first,
)

from .helpers import build, model, point

# A dense town already served by a centre, and two unserved villages.
POINTS = [
    point("town", 0, 0, 400),
    point("village-1", 10_000, 0, 120, risk=0.5),
    point("village-2", 20_000, 0, 100, risk=0.5),
]
SITES = [build("in-town", 0, 0), build("v1", 10_000, 0), build("v2", 20_000, 0)]
MODEL = model(10, SITES, POINTS)  # 1 km


def _input(budget: float, **constraints: frozenset[str]) -> PlanningInput:
    state = initial_state(POINTS)
    state.uncovered_0_2["town"] = 0.0  # the town is already covered
    state.uncovered_3_6["town"] = 0.0
    return PlanningInput(
        points=POINTS,
        base_state=state,
        candidates=SITES,
        weights=Weights(stunting=0.4, readiness=0.4, jobs=0.2),
        constraints=Constraints(budget=budget, **constraints),
        child_count_bounds={"A": (0.8, 1.2)},
    )


def test_respects_budget() -> None:
    plan = GreedyOptimizer(MODEL).plan(_input(budget=25))
    assert plan.outcomes.cost <= 25
    assert len(plan.suggestions) == 2


def test_never_picks_an_excluded_site() -> None:
    plan = GreedyOptimizer(MODEL).plan(_input(budget=100, excluded=frozenset({"v1"})))
    assert "v1" not in {s.candidate.id for s in plan.suggestions}


def test_access_problem_shrinks_the_catchment() -> None:
    points = [point("edge", 800, 0, 50)]
    data = PlanningInput(
        points=points,
        base_state=initial_state(points),
        candidates=[build("site", 0, 0)],
        weights=Weights(1, 1, 1),
        constraints=Constraints(budget=100, reduced_access=frozenset({"site"})),
        child_count_bounds={"A": (1.0, 1.0)},
    )
    assert GreedyOptimizer(MODEL).plan(data).suggestions == ()


def test_beats_largest_population_first() -> None:
    data = _input(budget=20)
    greedy = GreedyOptimizer(MODEL).plan(data)
    baseline = largest_population_first(MODEL, data)
    assert baseline.suggestions[0].candidate.id == "in-town"
    assert greedy.outcomes.children_reached.estimate > baseline.outcomes.children_reached.estimate


def test_impacts_carry_ranges_and_drivers() -> None:
    plan = GreedyOptimizer(MODEL).plan(_input(budget=100))
    for suggestion in plan.suggestions:
        reached = suggestion.impact.children_reached
        assert reached.low <= reached.estimate <= reached.high
        assert suggestion.drivers
