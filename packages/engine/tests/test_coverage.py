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
    taken = {pid: round(young + old, 6) for pid, young, old in assignment.from_points}
    assert taken == {"near": 30, "far": 10}


def test_places_are_shared_between_age_bands_unless_seat_is_3_to_6_only() -> None:
    model = StraightLineCoverage()
    points = [point("p", 0, 0, 100)]  # 40 aged 0-2, 60 aged 3-6
    mixed = model.assign(Seat("s", Position(0, 0), 50), points, initial_state(points))
    assert round(mixed.children_0_2) == 20
    school = model.assign(
        Seat("s", Position(0, 0), 50, serves_0_2=False), points, initial_state(points)
    )
    assert school.children_0_2 == 0 and round(school.children) == 50


def test_cover_never_exceeds_total_places() -> None:
    model = StraightLineCoverage()
    points = [point(f"p{i}", i * 300.0, 0, 25) for i in range(10)]
    seats = [Seat("a", Position(0, 0), 60), Seat("b", Position(2700, 0), 60)]
    state = cover(model, seats, points)
    covered = sum(p.children for p in points) - sum(state.uncovered(p.id) for p in points)
    assert covered == 120
