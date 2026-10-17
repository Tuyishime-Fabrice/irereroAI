from irerero_engine.coverage import Seat, cover, initial_state
from irerero_engine.travel import RoadNetwork, StraightLineTravel
from irerero_engine.types import Position

from .helpers import model, point


def test_catchment_follows_walking_minutes() -> None:
    seat = Seat("s", Position(0, 0), 100)
    points = [point("near", 999, 0, 10), point("far", 1001, 0, 10)]
    assert [p.id for p in model(10, [seat], points).reachable(seat, points)] == ["near"]


def test_a_reported_access_problem_shrinks_the_catchment() -> None:
    points = [point("p", 800, 0, 10)]
    coverage = model(10, [Seat("s", Position(0, 0), 100)], points)
    assert coverage.reachable(Seat("s", Position(0, 0), 100, radius_factor=0.5), points) == []


def test_assign_fills_nearest_first_up_to_capacity() -> None:
    seat = Seat("s", Position(0, 0), 40)
    points = [point("far", 2000, 0, 30), point("near", 100, 0, 30)]
    assignment = model(30, [seat], points).assign(seat, points, initial_state(points))
    taken = {pid: round(young + old, 6) for pid, young, old in assignment.from_points}
    assert taken == {"near": 30, "far": 10}


def test_places_are_shared_between_age_bands_unless_seat_is_3_to_6_only() -> None:
    points = [point("p", 0, 0, 100)]  # 40 aged 0-2, 60 aged 3-6
    seat = Seat("s", Position(0, 0), 50)
    coverage = model(30, [seat], points)
    mixed = coverage.assign(seat, points, initial_state(points))
    assert round(mixed.children_0_2) == 20
    school = coverage.assign(
        Seat("s", Position(0, 0), 50, serves_0_2=False), points, initial_state(points)
    )
    assert school.children_0_2 == 0 and round(school.children) == 50


def test_cover_never_exceeds_total_places() -> None:
    points = [point(f"p{i}", i * 300.0, 0, 25) for i in range(10)]
    seats = [Seat("a", Position(0, 0), 60), Seat("b", Position(2700, 0), 60)]
    state = cover(model(30, seats, points), seats, points)
    covered = sum(p.children for p in points) - sum(state.uncovered(p.id) for p in points)
    assert covered == 120


def test_straight_line_applies_the_detour_factor() -> None:
    travel = StraightLineTravel(metres_per_minute=100, detour=1.5)
    assert travel.minutes(Position(0, 0), [Position(1000, 0), Position(3000, 0)], 20) == [
        15.0,
        None,
    ]


def test_road_network_walks_around_a_river() -> None:
    # Two banks 200 m apart; the only bridge is 1 km upstream.
    nodes = {
        1: Position(0, 0),
        2: Position(0, 1000),
        3: Position(200, 1000),
        4: Position(200, 0),
    }
    road = RoadNetwork(nodes, [(1, 2), (2, 3), (3, 4)], metres_per_minute=100, detour=1.0)
    [minutes] = road.minutes(Position(0, 0), [Position(200, 0)], 60)
    # Straight across is 2 minutes, which the network never beats here: walking the road
    # takes 22, so the off-road straight walk is the shortest estimate.
    assert minutes == 2.0
    blocked = RoadNetwork(nodes, [(1, 2), (2, 3), (3, 4)], metres_per_minute=100, detour=20.0)
    [around] = blocked.minutes(Position(0, 0), [Position(200, 0)], 60)
    assert around == 22.0
