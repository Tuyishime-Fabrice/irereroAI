from sqlalchemy import Connection

from irerero_api.engine_io.candidates import candidates, rejection_constraints
from irerero_api.engine_io.catchments import walking_minutes
from irerero_api.engine_io.centres import seats
from irerero_api.engine_io.points import demand_points
from irerero_engine.coverage import CatchmentCoverage, cover
from irerero_engine.optimizer import PlanningInput, Weights
from irerero_engine.travel import DEFAULT_DETOUR, DEFAULT_METRES_PER_MINUTE


def coverage_model(conn: Connection, district: str, catchment_minutes: int) -> CatchmentCoverage:
    return CatchmentCoverage(catchment_minutes, walking_minutes(conn, district))


def planning_input(
    conn: Connection,
    district: str,
    budget: float,
    weights: Weights,
    model: CatchmentCoverage,
    excluded_by_user: frozenset[str] = frozenset(),
) -> PlanningInput:
    points, bounds = demand_points(conn, district)
    base = cover(model, seats(conn, district), points)
    # Parent requests and crowded centres count as "near" a site within a straight-line radius
    # equivalent to the catchment.
    radius = model.catchment_minutes * DEFAULT_METRES_PER_MINUTE / DEFAULT_DETOUR
    return PlanningInput(
        points=points,
        base_state=base,
        candidates=candidates(conn, district, radius),
        weights=weights,
        constraints=rejection_constraints(conn, district, budget, excluded_by_user),
        child_count_bounds=bounds,
    )
