"""CoverageModel: which children have a reachable place.

Phase 1 baseline: straight-line catchments. Walking minutes convert to metres with an adjustable
factor, and children are matched to the nearest centres until each centre's capacity is used.
Phase 2: OSM walking-time catchments implement the same interface.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from irerero_engine.types import Position

DEFAULT_METRES_PER_MINUTE = 67.0  # about 4 km/h on rural paths
DEFAULT_CATCHMENT_MINUTES = 30
# Catchments precomputed by the build, so the planner's slider answers instantly.
CATCHMENT_STEPS = (15, 20, 30, 45, 60)


@dataclass(frozen=True)
class DemandPoint:
    """Children living around one grid point, with the need of the area they belong to."""

    id: str
    position: Position
    area_code: str
    children_0_2: float
    children_3_6: float
    stunting_risk: float
    mothers_barrier_share: float
    # Interval bounds of the two shares; equal to the estimates when unknown.
    stunting_risk_bounds: tuple[float, float] | None = None
    mothers_barrier_bounds: tuple[float, float] | None = None

    def risk(self, bound: int | None) -> float:
        """Stunting risk at the estimate (None), lower (0) or upper (1) bound."""
        if bound is None or self.stunting_risk_bounds is None:
            return self.stunting_risk
        return self.stunting_risk_bounds[bound]

    def barrier(self, bound: int | None) -> float:
        if bound is None or self.mothers_barrier_bounds is None:
            return self.mothers_barrier_share
        return self.mothers_barrier_bounds[bound]

    @property
    def children(self) -> float:
        return self.children_0_2 + self.children_3_6


@dataclass(frozen=True)
class Seat:
    """A centre or a planned site offering places."""

    id: str
    position: Position
    places: int
    radius_factor: float = 1.0
    serves_0_2: bool = True


@dataclass
class CoverageState:
    """Children still without a place, per demand point and age band."""

    uncovered_0_2: dict[str, float]
    uncovered_3_6: dict[str, float]
    covered_by_seat: dict[str, float] = field(default_factory=dict)

    def uncovered(self, point_id: str) -> float:
        return self.uncovered_0_2[point_id] + self.uncovered_3_6[point_id]

    def copy(self) -> "CoverageState":
        return CoverageState(
            dict(self.uncovered_0_2), dict(self.uncovered_3_6), dict(self.covered_by_seat)
        )


@dataclass(frozen=True)
class Assignment:
    """Children one seat takes from each point, by age band."""

    seat_id: str
    from_points: tuple[tuple[str, float, float], ...]  # (point id, children 0-2, children 3-6)

    @property
    def children(self) -> float:
        return sum(young + old for _, young, old in self.from_points)

    @property
    def children_0_2(self) -> float:
        return sum(young for _, young, _ in self.from_points)


class CoverageModel(Protocol):
    version: str
    catchment_minutes: int

    def reachable(self, seat: Seat, points: Sequence[DemandPoint]) -> list[DemandPoint]: ...

    def assign(
        self, seat: Seat, points: Sequence[DemandPoint], state: CoverageState
    ) -> Assignment: ...


class StraightLineCoverage:
    version = "coverage-straight-line-1"

    def __init__(
        self,
        catchment_minutes: int = DEFAULT_CATCHMENT_MINUTES,
        metres_per_minute: float = DEFAULT_METRES_PER_MINUTE,
    ) -> None:
        self.catchment_minutes = catchment_minutes
        self.metres_per_minute = metres_per_minute

    @property
    def radius_metres(self) -> float:
        return self.catchment_minutes * self.metres_per_minute

    def radius(self, seat: Seat) -> float:
        return self.radius_metres * seat.radius_factor

    def reachable(self, seat: Seat, points: Sequence[DemandPoint]) -> list[DemandPoint]:
        limit = self.radius(seat)
        near = [p for p in points if p.position.distance_to(seat.position) <= limit]
        return sorted(near, key=lambda p: (p.position.distance_to(seat.position), p.id))

    def assign(self, seat: Seat, points: Sequence[DemandPoint], state: CoverageState) -> Assignment:
        """Nearest children first; at each point, places are shared between the age bands in
        proportion to the children still waiting. Seats for 3 to 6 only take older children.

        Does not change `state`; call `apply` to commit.
        """
        remaining = float(seat.places)
        taken: list[tuple[str, float, float]] = []
        for point in self.reachable(seat, points):
            if remaining <= 0:
                break
            young_left = state.uncovered_0_2[point.id] if seat.serves_0_2 else 0.0
            old_left = state.uncovered_3_6[point.id]
            waiting = young_left + old_left
            if waiting <= 0:
                continue
            share = min(1.0, remaining / waiting)
            young, old = young_left * share, old_left * share
            remaining -= young + old
            taken.append((point.id, young, old))
        return Assignment(seat.id, tuple(taken))


def apply(state: CoverageState, assignment: Assignment) -> None:
    for point_id, young, old in assignment.from_points:
        state.uncovered_0_2[point_id] -= young
        state.uncovered_3_6[point_id] -= old
    state.covered_by_seat[assignment.seat_id] = (
        state.covered_by_seat.get(assignment.seat_id, 0.0) + assignment.children
    )


def initial_state(points: Sequence[DemandPoint]) -> CoverageState:
    return CoverageState(
        {p.id: p.children_0_2 for p in points}, {p.id: p.children_3_6 for p in points}
    )


def cover(
    model: CoverageModel, seats: Sequence[Seat], points: Sequence[DemandPoint]
) -> CoverageState:
    """Match children to existing places. Smaller catchments first so remote centres keep theirs."""
    state = initial_state(points)
    for seat in sorted(seats, key=lambda s: (len(model.reachable(s, points)), s.id)):
        apply(state, model.assign(seat, points, state))
    return state
