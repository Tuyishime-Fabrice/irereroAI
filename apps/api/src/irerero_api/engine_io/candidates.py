from sqlalchemy import Connection, text

from irerero_contract.enums import RejectionReason
from irerero_engine.optimizer import Action, Candidate, Constraints
from irerero_engine.types import Position, Range

ACTION_BY_KIND = {
    "village": Action.BUILD,
    "school": Action.BUILD,
    "centre_upgrade": Action.UPGRADE,
    "centre_support": Action.SUPPORT,
}
SEVERITY = {"critical": 1.0, "warning": 0.6}
LOW_RELIABILITY = 0.6
LOW_RELIABILITY_SEVERITY = 0.3
EXCLUDING = {
    RejectionReason.NO_LAND,
    RejectionReason.ALREADY_FUNDED,
    RejectionReason.COMMUNITY_OBJECTION,
}

QUERY = text(
    """
    SELECT s.id, s.kind, s.name, s.sector_code, s.centre_code,
        ST_X(ST_Transform(s.location, 32735)) AS x, ST_Y(ST_Transform(s.location, 32735)) AS y,
        u.cost_rwf, u.cost_low_rwf, u.cost_high_rwf, u.places_added,
        c.reliability_score,
        (SELECT r.enrolled_0_2_female + r.enrolled_0_2_male + r.enrolled_3_6_female
            + r.enrolled_3_6_male FROM weekly_report r WHERE r.centre_code = s.centre_code
            ORDER BY r.week_start DESC LIMIT 1) AS enrolled,
        (SELECT max(CASE a.severity WHEN 'critical' THEN 2 WHEN 'warning' THEN 1 ELSE 0 END)
            FROM alert a WHERE a.centre_code = s.centre_code AND a.status <> 'resolved')
            AS alert_level,
        (SELECT count(*) FROM demand_signal d WHERE ST_DWithin(
            ST_Transform(d.cell_centre, 32735), ST_Transform(s.location, 32735), :radius))
            AS demand,
        (SELECT count(DISTINCT a.centre_code) FROM alert a JOIN centre n ON n.code = a.centre_code
            WHERE a.kind = 'overcrowding' AND a.status <> 'resolved' AND ST_DWithin(
            ST_Transform(n.location, 32735), ST_Transform(s.location, 32735), :radius))
            AS crowded
    FROM candidate_site s
    JOIN admin_unit sector ON sector.code = s.sector_code
    JOIN unit_cost u ON u.band = s.unit_cost_band AND u.action = CASE s.kind
        WHEN 'centre_upgrade' THEN 'upgrade' WHEN 'centre_support' THEN 'support' ELSE 'build' END
    LEFT JOIN centre c ON c.code = s.centre_code
    WHERE sector.parent_code = :district
    ORDER BY s.id
    """
)


def _severity(alert_level: int | None, reliability: float | None) -> float:
    if alert_level == 2:
        return SEVERITY["critical"]
    if alert_level == 1:
        return SEVERITY["warning"]
    if reliability is not None and reliability < LOW_RELIABILITY:
        return LOW_RELIABILITY_SEVERITY
    return 0.0


def candidates(conn: Connection, district: str, radius_metres: float) -> list[Candidate]:
    rows = conn.execute(QUERY, {"district": district, "radius": radius_metres})
    result = []
    for row in rows:
        action = ACTION_BY_KIND[row.kind]
        support = action is Action.SUPPORT
        result.append(
            Candidate(
                id=row.id,
                action=action,
                name=row.name,
                area_code=row.sector_code,
                position=Position(row.x, row.y),
                cost=Range(row.cost_rwf, row.cost_low_rwf, row.cost_high_rwf),
                places_added=row.places_added,
                centre_code=row.centre_code,
                serves_0_2=row.kind != "school",
                support_children=float(row.enrolled or 0) if support else 0.0,
                severity=_severity(row.alert_level, row.reliability_score) if support else 0.0,
                parent_demand=row.demand,
                overcrowded_nearby=row.crowded,
            )
        )
    return result


def rejection_constraints(
    conn: Connection, district: str, budget: float, excluded_by_user: frozenset[str]
) -> Constraints:
    """Turn every earlier rejection in this district into a constraint for the next run."""
    rows = conn.execute(
        text(
            "SELECT r.site_id, d.reason_code FROM decision d "
            "JOIN recommendation r ON r.id = d.recommendation_id "
            "JOIN scenario s ON s.id = r.scenario_id "
            "WHERE s.district_code = :district AND d.verdict = 'reject'"
        ),
        {"district": district},
    ).all()
    excluded = {site for site, reason in rows if reason in {r.value for r in EXCLUDING}}
    reduced = {site for site, reason in rows if reason == RejectionReason.ACCESS_PROBLEM.value}
    return Constraints(
        budget=budget,
        excluded=frozenset(excluded) | excluded_by_user,
        reduced_access=frozenset(reduced),
    )
