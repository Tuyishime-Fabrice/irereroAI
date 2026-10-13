from irerero_engine.coverage import DemandPoint
from irerero_engine.optimizer import Action, Candidate
from irerero_engine.types import Position, Range


def point(
    pid: str, x: float, y: float, children: float, risk: float = 0.3, area: str = "A"
) -> DemandPoint:
    return DemandPoint(pid, Position(x, y), area, children * 0.4, children * 0.6, risk, 0.3)


def build(
    cid: str, x: float, y: float, cost: float = 10.0, places: int = 50, area: str = "A"
) -> Candidate:
    return Candidate(cid, Action.BUILD, cid, area, Position(x, y), Range(cost, cost, cost), places)
