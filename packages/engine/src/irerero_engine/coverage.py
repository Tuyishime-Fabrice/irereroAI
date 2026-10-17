"""CoverageModel: which children have a reachable place.

Catchments are walking minutes from each centre or site to each population cell, precomputed
by the build (see travel.py). Children are matched to the nearest places, by walking time,
until each place's capacity is used.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from irerero_engine.travel import TravelTimes
from irerero_engine.types import Position

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


Minutes = Mapping[str, Mapping[str, float]]
"""Seat id -> population cell id -> walking minutes, for cells within the longest step."""


class Located(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def position(self) -> Position: ...


def catchments(
    travel: TravelTimes,
    seats: Sequence[Located],
    points: Sequence[Located],
    limit: float = max(CATCHMENT_STEPS),
) -> dict[str, dict[str, float]]:
    """Walking minutes from each seat to every point within `limit` minutes."""
    positions = [p.position for p in points]
    out: dict[str, dict[str, float]] = {}
    for seat in seats:
        times = travel.minutes(seat.position, positions, limit)
        out[seat.id] = {
            point.id: minutes
            for point, minutes in zip(points, times, strict=True)
            if minutes is not None
        }
    return out


class CatchmentCoverage:
    """Coverage over precomputed walking minutes."""

    version = "coverage-walking-time-1"

    def __init__(self, catchment_minutes: int, minutes: Minutes) -> None:
        self.catchment_minutes = catchment_minutes
        self.minutes = minutes
        self._ordered = {
            seat: sorted((m, pid) for pid, m in cells.items()) for seat, cells in minutes.items()
        }
        self._index: tuple[Sequence[DemandPoint], dict[str, DemandPoint]] | None = None

    def _by_id(self, points: Sequence[DemandPoint]) -> dict[str, DemandPoint]:
        # The optimizer passes the same list many times; index it once.
        if self._index is None or self._index[0] is not points:
            self._index = (points, {p.id: p for p in points})
        return self._index[1]

    def reachable(self, seat: Seat, points: Sequence[DemandPoint]) -> list[DemandPoint]:
        """Points within the catchment, nearest first. A smaller radius factor (an access
        problem a planner reported) shrinks the catchment in proportion."""
        limit = self.catchment_minutes * seat.radius_factor
        by_id = self._by_id(points)
        out = []
        for minutes, pid in self._ordered.get(seat.id, ()):
            if minutes > limit:
                break
            point = by_id.get(pid)
            if point is not None:
                out.append(point)
        return out

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
