from collections.abc import Sequence

from irerero_engine.coverage import CatchmentCoverage, DemandPoint, Seat, catchments
from irerero_engine.optimizer import Action, Candidate
from irerero_engine.travel import StraightLineTravel
from irerero_engine.types import Position, Range

# 100 m per minute in a straight line keeps test distances easy to read.
TRAVEL = StraightLineTravel(metres_per_minute=100, detour=1.0)


def model(
    minutes: int, seats: Sequence[Seat | Candidate], points: Sequence[DemandPoint]
) -> CatchmentCoverage:
    as_seats = [s if isinstance(s, Seat) else Seat(s.id, s.position, s.places_added) for s in seats]
    return CatchmentCoverage(minutes, catchments(TRAVEL, as_seats, points))


def point(
    pid: str, x: float, y: float, children: float, risk: float = 0.3, area: str = "A"
) -> DemandPoint:
    return DemandPoint(pid, Position(x, y), area, children * 0.4, children * 0.6, risk, 0.3)


def build(
    cid: str, x: float, y: float, cost: float = 10.0, places: int = 50, area: str = "A"
) -> Candidate:
    return Candidate(cid, Action.BUILD, cid, area, Position(x, y), Range(cost, cost, cost), places)
