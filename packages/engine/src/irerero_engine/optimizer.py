"""SiteOptimizer: a ranked, budget-feasible shortlist of build, upgrade and support actions.

Phase 1 baseline: greedy maximal coverage. Each round takes the action with the highest
weighted benefit per franc that still fits the budget, given what earlier picks already cover.
Phase 2: an OR-Tools or PuLP formulation implements the same interface.

Outputs are countable only: children reached, uncovered children remaining, high-risk children
reached, and mothers of under-3s reached who report childcare as a barrier. The optimizer never
estimates a change in stunting.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from statistics import mean, pstdev
from typing import Protocol

from irerero_engine.coverage import (
    Assignment,
    CoverageModel,
    CoverageState,
    DemandPoint,
    Seat,
    apply,
)
from irerero_engine.features import FEATURES
from irerero_engine.types import Driver, Position, Range

# Every child counts; the policy weights decide how much extra each kind of child counts.
BASE_VALUE = 0.25
# A support action protects existing places rather than creating new ones, so it counts less
# per child than a new place.
SUPPORT_FACTOR = 0.5
ACCESS_PROBLEM_RADIUS = 0.5
# Parents asking for a centre near a site is direct evidence that places would be used: up to
# +30% value once ten or more requests or empty searches fall in the catchment.
DEMAND_BOOST = 0.3
DEMAND_CAP = 10
# A driver is shown only when the site stands out from the others by this many deviations.
DRIVER_MIN_Z = 0.5
# Value per franc is how sites are ranked, so it is shown only when it is exceptional.
LOW_COST_MIN_Z = 1.0


class Action(StrEnum):
    BUILD = "build"
    UPGRADE = "upgrade"
    SUPPORT = "support"


@dataclass(frozen=True)
class Weights:
    stunting: float
    readiness: float
    jobs: float

    def normalised(self) -> "Weights":
        total = self.stunting + self.readiness + self.jobs
        if total <= 0:
            return Weights(1 / 3, 1 / 3, 1 / 3)
        return Weights(self.stunting / total, self.readiness / total, self.jobs / total)


@dataclass(frozen=True)
class Candidate:
    id: str
    action: Action
    name: str
    area_code: str
    position: Position
    cost: Range
    places_added: int
    centre_code: str | None = None
    serves_0_2: bool = True
    support_children: float = 0.0
    severity: float = 0.0
    parent_demand: int = 0
    overcrowded_nearby: int = 0


@dataclass(frozen=True)
class Constraints:
    budget: float
    excluded: frozenset[str] = frozenset()
    reduced_access: frozenset[str] = frozenset()
    max_actions_per_area: int | None = None


@dataclass(frozen=True)
class PlanningInput:
    points: Sequence[DemandPoint]
    base_state: CoverageState
    candidates: Sequence[Candidate]
    weights: Weights
    constraints: Constraints
    # Per area: (low / estimate, high / estimate) of the child counts, for impact ranges.
    child_count_bounds: Mapping[str, tuple[float, float]]
    # Sites a person already approved: kept, in this order, before anything new is added.
    preselected: tuple[str, ...] = ()


@dataclass(frozen=True)
class Impact:
    children_reached: Range
    children_0_2_reached: float
    high_risk_reached: Range
    mothers_under3_reached: Range
    children_supported: float


@dataclass(frozen=True)
class Suggestion:
    rank: int
    candidate: Candidate
    impact: Impact
    score: float
    drivers: tuple[Driver, ...]


@dataclass(frozen=True)
class Outcomes:
    children_reached: Range
    uncovered_remaining: Range
    high_risk_reached: Range
    mothers_under3_reached: Range
    children_supported: float
    cost: float


@dataclass(frozen=True)
class Plan:
    suggestions: tuple[Suggestion, ...]
    outcomes: Outcomes
    optimizer_version: str


class SiteOptimizer(Protocol):
    version: str

    def plan(self, data: PlanningInput) -> Plan: ...


@dataclass
class _Valuer:
    """Value of reaching a child. Risk and barrier are scaled to the district's highest value,
    so each weight moves the ranking by a comparable amount."""

    weights: Weights
    max_risk: float
    max_barrier: float
    points: Mapping[str, DemandPoint] = field(default_factory=dict)

    def child_value(self, point: DemandPoint, young: float, old: float) -> float:
        w = self.weights
        risk = point.stunting_risk / self.max_risk if self.max_risk else 0.0
        barrier = point.mothers_barrier_share / self.max_barrier if self.max_barrier else 0.0
        return (
            (BASE_VALUE + w.stunting * risk) * (young + old)
            + w.readiness * old
            + w.jobs * barrier * young
        )

    def assignment_value(self, assignment: Assignment) -> float:
        return sum(
            self.child_value(self.points[pid], young, old)
            for pid, young, old in assignment.from_points
        )

    def support_value(self, candidate: Candidate, area_risk: float, area_barrier: float) -> float:
        w = self.weights
        risk = area_risk / self.max_risk if self.max_risk else 0.0
        barrier = area_barrier / self.max_barrier if self.max_barrier else 0.0
        # Enrolled children are assumed to be about 60% aged 3 to 6.
        per_child = BASE_VALUE + w.stunting * risk + w.readiness * 0.6 + w.jobs * barrier * 0.4
        return SUPPORT_FACTOR * candidate.severity * candidate.support_children * per_child


def _seat(candidate: Candidate, constraints: Constraints) -> Seat:
    factor = ACCESS_PROBLEM_RADIUS if candidate.id in constraints.reduced_access else 1.0
    return Seat(
        candidate.id, candidate.position, candidate.places_added, factor, candidate.serves_0_2
    )


def _area_means(points: Sequence[DemandPoint]) -> dict[str, tuple[float, float]]:
    by_area: dict[str, list[DemandPoint]] = {}
    for point in points:
        by_area.setdefault(point.area_code, []).append(point)
    return {
        area: (mean(p.stunting_risk for p in pts), mean(p.mothers_barrier_share for p in pts))
        for area, pts in by_area.items()
    }


def _scaled_state(
    state: CoverageState, points: Sequence[DemandPoint], factors: Mapping[str, float]
) -> CoverageState:
    scaled = state.copy()
    for p in points:
        factor = factors.get(p.area_code, 1.0)
        scaled.uncovered_0_2[p.id] *= factor
        scaled.uncovered_3_6[p.id] *= factor
    return scaled


def _scaled_points(
    points: Sequence[DemandPoint], factors: Mapping[str, float]
) -> list[DemandPoint]:
    return [
        DemandPoint(
            p.id,
            p.position,
            p.area_code,
            p.children_0_2 * factors.get(p.area_code, 1.0),
            p.children_3_6 * factors.get(p.area_code, 1.0),
            p.stunting_risk,
            p.mothers_barrier_share,
        )
        for p in points
    ]


@dataclass(frozen=True)
class _Evaluation:
    impacts: tuple[Impact, ...]
    outcomes: Outcomes


def evaluate(model: CoverageModel, data: PlanningInput, chosen: Sequence[Candidate]) -> _Evaluation:
    """Countable outcomes of a sequence of actions, with low and high child counts."""
    points_by_id = {p.id: p for p in data.points}
    runs: dict[str, list[float]] = {}
    totals: dict[str, float] = {}
    for bound, index in (("estimate", None), ("low", 0), ("high", 1)):
        factors = {
            area: 1.0 if index is None else bounds[index]
            for area, bounds in data.child_count_bounds.items()
        }
        points = _scaled_points(data.points, factors)
        state = _scaled_state(data.base_state, data.points, factors)
        reached = []
        for candidate in chosen:
            if candidate.action is Action.SUPPORT:
                reached.append(0.0)
                continue
            assignment = model.assign(_seat(candidate, data.constraints), points, state)
            apply(state, assignment)
            reached.append(assignment.children)
        runs[bound] = reached
        totals[bound] = sum(state.uncovered(p.id) for p in points)

    impacts = []
    state = data.base_state.copy()
    supported_total = 0.0
    risk_totals = [0.0, 0.0, 0.0]
    mother_totals = [0.0, 0.0, 0.0]
    for i, candidate in enumerate(chosen):
        if candidate.action is Action.SUPPORT:
            # Support protects existing places; it reaches no new children.
            zero = Range(0, 0, 0)
            impact = Impact(zero, 0.0, zero, zero, candidate.support_children)
        else:
            assignment = model.assign(_seat(candidate, data.constraints), data.points, state)
            apply(state, assignment)
            risk = [
                sum((y + o) * points_by_id[pid].risk(b) for pid, y, o in assignment.from_points)
                for b in (None, 0, 1)
            ]
            mothers = [
                sum(y * points_by_id[pid].barrier(b) for pid, y, _ in assignment.from_points)
                for b in (None, 0, 1)
            ]
            low, high = sorted((runs["low"][i], runs["high"][i]))
            estimate = runs["estimate"][i]
            impact = Impact(
                Range(estimate, min(low, estimate), max(high, estimate)),
                assignment.children_0_2,
                Range(*risk),
                Range(*mothers),
                0.0,
            )
            risk_totals = [t + v for t, v in zip(risk_totals, risk, strict=True)]
            mother_totals = [t + v for t, v in zip(mother_totals, mothers, strict=True)]
        supported_total += impact.children_supported
        impacts.append(impact)

    reached_total = Range(*(sum(runs[b]) for b in ("estimate", "low", "high")))
    uncovered = Range(totals["estimate"], *sorted((totals["low"], totals["high"])))
    return _Evaluation(
        tuple(impacts),
        Outcomes(
            reached_total,
            uncovered,
            Range(*risk_totals),
            Range(*mother_totals),
            supported_total,
            sum(c.cost.estimate for c in chosen),
        ),
    )


def _drivers(
    metrics: Mapping[str, Mapping[str, float]], candidate: Candidate
) -> tuple[Driver, ...]:
    """Top three features where this candidate stands out from the others of its kind."""
    group = "support" if candidate.action is Action.SUPPORT else "places"
    candidate_id = candidate.id
    scores = []
    for key, values in metrics.items():
        prefix, feature = key.split(":")
        if prefix != group or candidate_id not in values:
            continue
        pool = list(values.values())
        spread = pstdev(pool) or 1.0
        z = (values.get(candidate_id, 0.0) - mean(pool)) / spread
        threshold = LOW_COST_MIN_Z if feature == "low_cost" else DRIVER_MIN_Z
        if z >= threshold:
            scores.append((z, feature))
    top = sorted(scores, reverse=True)[:3]
    total = sum(z for z, _ in top) or 1.0
    return tuple(
        Driver(f, FEATURES[f].label_en, FEATURES[f].label_rw, round(z / total, 3)) for z, f in top
    )


class GreedyOptimizer:
    version = "optimizer-greedy-1"

    def __init__(self, model: CoverageModel) -> None:
        self.model = model

    def plan(self, data: PlanningInput) -> Plan:
        constraints = data.constraints
        weights = data.weights.normalised()
        max_risk = max((p.stunting_risk for p in data.points), default=0.0)
        max_barrier = max((p.mothers_barrier_share for p in data.points), default=0.0)
        valuer = _Valuer(weights, max_risk, max_barrier, {p.id: p for p in data.points})
        area_means = _area_means(data.points)
        state = data.base_state.copy()
        remaining = constraints.budget
        chosen: list[Candidate] = []
        scores: list[float] = []
        per_area: dict[str, int] = {}
        pool = [c for c in data.candidates if c.id not in constraints.excluded]
        metrics: dict[str, dict[str, float]] = {}
        for candidate in pool:
            value, _ = self._value(candidate, valuer, area_means, state, constraints)
            self._record(metrics, candidate, value, state, constraints, valuer)
        by_id = {c.id: c for c in data.candidates}
        for site_id in data.preselected:
            candidate = by_id[site_id]
            value, assignment = self._value(candidate, valuer, area_means, state, constraints)
            if assignment is not None:
                apply(state, assignment)
            chosen.append(candidate)
            scores.append(value / candidate.cost.estimate)
            remaining -= candidate.cost.estimate
            per_area[candidate.area_code] = per_area.get(candidate.area_code, 0) + 1

        while True:
            best: tuple[float, Candidate, Assignment | None] | None = None
            for candidate in pool:
                if candidate in chosen or candidate.cost.estimate > remaining:
                    continue
                limit = constraints.max_actions_per_area
                if limit is not None and per_area.get(candidate.area_code, 0) >= limit:
                    continue
                value, assignment = self._value(candidate, valuer, area_means, state, constraints)
                if value <= 0:
                    continue
                ratio = value / candidate.cost.estimate
                if (
                    best is None
                    or ratio > best[0]
                    or (ratio == best[0] and candidate.id < best[1].id)
                ):
                    best = (ratio, candidate, assignment)
            if best is None:
                break
            ratio, candidate, assignment = best
            if assignment is not None:
                apply(state, assignment)
            chosen.append(candidate)
            scores.append(ratio)
            remaining -= candidate.cost.estimate
            per_area[candidate.area_code] = per_area.get(candidate.area_code, 0) + 1

        evaluation = evaluate(self.model, data, chosen)
        suggestions = tuple(
            Suggestion(rank, candidate, impact, score * 1_000_000, _drivers(metrics, candidate))
            for rank, (candidate, impact, score) in enumerate(
                zip(chosen, evaluation.impacts, scores, strict=True), start=1
            )
        )
        return Plan(suggestions, evaluation.outcomes, self.version)

    def _value(
        self,
        candidate: Candidate,
        valuer: _Valuer,
        area_means: Mapping[str, tuple[float, float]],
        state: CoverageState,
        constraints: Constraints,
    ) -> tuple[float, Assignment | None]:
        if candidate.action is Action.SUPPORT:
            risk, barrier = area_means.get(candidate.area_code, (0.0, 0.0))
            return valuer.support_value(candidate, risk, barrier), None
        seat = _seat(candidate, constraints)
        assignment = self.model.assign(seat, list(valuer.points.values()), state)
        boost = 1 + DEMAND_BOOST * min(candidate.parent_demand, DEMAND_CAP) / DEMAND_CAP
        return valuer.assignment_value(assignment) * boost, assignment

    def _record(
        self,
        metrics: dict[str, dict[str, float]],
        candidate: Candidate,
        value: float,
        state: CoverageState,
        constraints: Constraints,
        valuer: _Valuer,
    ) -> None:
        """Before-any-pick metrics, so drivers compare each site with the others of its kind."""
        group = "support" if candidate.action is Action.SUPPORT else "places"

        def put(feature: str, amount: float) -> None:
            metrics.setdefault(f"{group}:{feature}", {})[candidate.id] = amount

        put("low_cost", value / candidate.cost.estimate * 1_000_000)
        put("overcrowding", float(candidate.overcrowded_nearby))
        if group == "support":
            put("report_problems", candidate.severity)
            return
        reachable = self.model.reachable(
            _seat(candidate, constraints), list(valuer.points.values())
        )
        waiting = sum(state.uncovered(p.id) for p in reachable)
        put("uncovered_children", waiting)
        put("parent_demand", float(candidate.parent_demand))
        if waiting:
            put(
                "stunting_risk",
                sum(state.uncovered(p.id) * p.stunting_risk for p in reachable) / waiting,
            )
            young = sum(state.uncovered_0_2[p.id] for p in reachable)
            if young:
                put(
                    "mothers_barrier",
                    sum(state.uncovered_0_2[p.id] * p.mothers_barrier_share for p in reachable)
                    / young,
                )


def largest_population_first(model: CoverageModel, data: PlanningInput) -> Plan:
    """Comparison baseline: biggest catchment population first, ignoring weights and coverage."""
    constraints = data.constraints
    builds = [
        c
        for c in data.candidates
        if c.action is not Action.SUPPORT and c.id not in constraints.excluded
    ]

    def population(candidate: Candidate) -> float:
        return sum(p.children for p in model.reachable(_seat(candidate, constraints), data.points))

    remaining = constraints.budget
    chosen = []
    for candidate in sorted(builds, key=lambda c: (-population(c), c.id)):
        if candidate.cost.estimate <= remaining:
            chosen.append(candidate)
            remaining -= candidate.cost.estimate
    evaluation = evaluate(model, data, chosen)
    suggestions = tuple(
        Suggestion(rank, candidate, impact, 0.0, ())
        for rank, (candidate, impact) in enumerate(zip(chosen, evaluation.impacts, strict=True), 1)
    )
    return Plan(suggestions, evaluation.outcomes, "baseline-largest-population-1")
