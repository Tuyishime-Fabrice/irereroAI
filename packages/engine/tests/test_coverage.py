from irerero_engine.coverage import Seat, StraightLineCoverage, cover, initial_state
from irerero_engine.types import Position

from .helpers import point


def test_catchment_radius_follows_minutes_and_speed() -> None:
    model = StraightLineCoverage(catchment_minutes=10, metres_per_minute=100)
    seat = Seat("s", Position(0, 0), 100)
    points = [point("near", 999, 0, 10), point("far", 1001, 0, 10)]
    assert [p.id for p in model.reachable(seat, points)] == ["near"]


def test_assign_fills_nearest_first_up_to_capacity() -> None:
    model = StraightLineCoverage(catchment_minutes=30, metres_per_minute=100)
    points = [point("far", 2000, 0, 30), point("near", 100, 0, 30)]
    state = initial_state(points)
    assignment = model.assign(Seat("s", Position(0, 0), 40), points, state)
    taken = {pid: young + old for pid, young, old in assignment.from_points}
    assert taken == {"near": 30, "far": 10}


def test_cover_never_exceeds_total_places() -> None:
    model = StraightLineCoverage()
    points = [point(f"p{i}", i * 300.0, 0, 25) for i in range(10)]
    seats = [Seat("a", Position(0, 0), 60), Seat("b", Position(2700, 0), 60)]
    state = cover(model, seats, points)
    covered = sum(p.children for p in points) - sum(state.uncovered(p.id) for p in points)
    assert covered == 120
