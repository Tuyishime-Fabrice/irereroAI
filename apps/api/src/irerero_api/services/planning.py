from datetime import date

from sqlalchemy import Connection

from irerero_api.engine_io.candidates import candidates, rejection_constraints
from irerero_api.engine_io.centres import seats
from irerero_api.engine_io.points import demand_points
from irerero_engine.coverage import StraightLineCoverage, cover
from irerero_engine.optimizer import PlanningInput, Weights


def planning_input(
    conn: Connection,
    district: str,
    week: date,
    budget: float,
    weights: Weights,
    model: StraightLineCoverage,
    excluded_by_user: frozenset[str] = frozenset(),
) -> PlanningInput:
    points, bounds = demand_points(conn, district)
    base = cover(model, seats(conn, district, week), points)
    return PlanningInput(
        points=points,
        base_state=base,
        candidates=candidates(conn, district, model.radius_metres),
        weights=weights,
        constraints=rejection_constraints(conn, district, budget, excluded_by_user),
        child_count_bounds=bounds,
    )
