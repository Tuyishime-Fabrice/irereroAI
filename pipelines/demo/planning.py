"""Simulated unit costs and candidate sites for the Gicumbi plan workspace."""

from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import Action, CandidateKind, CostBand
from pipelines.demo.config import DEMO_DISTRICT, REFERENCE_YEAR, SOURCE, rng

# (cost in RWF, places added). Simulated: Phase 2 replaces them with MINEDUC and NCDA unit costs.
# Upgrades mainly raise quality, so they add few places for their cost.
UNIT_COSTS = {
    (Action.BUILD, CostBand.LOW): (18_000_000, 60),
    (Action.BUILD, CostBand.MEDIUM): (25_000_000, 80),
    (Action.BUILD, CostBand.HIGH): (35_000_000, 100),
    (Action.UPGRADE, CostBand.LOW): (4_500_000, 10),
    (Action.UPGRADE, CostBand.MEDIUM): (6_500_000, 15),
    (Action.UPGRADE, CostBand.HIGH): (9_000_000, 20),
    (Action.SUPPORT, CostBand.LOW): (800_000, 0),
    (Action.SUPPORT, CostBand.MEDIUM): (1_200_000, 0),
    (Action.SUPPORT, CostBand.HIGH): (2_000_000, 0),
}
COST_SPREAD = 0.25
# The demo story: the first Cyumba village site is the cheapest build in the under-served
# sector, and the planner rejects it in the tour because no land is available.
STORY_SITE_BANDS = {"SITE-CYUMBA-V1": CostBand.LOW}
LETTERS = "ABC"


def load_unit_costs(conn: Connection, run_id: object) -> int:
    rows = [
        {
            "action": action.value,
            "band": band.value,
            "cost": cost,
            "low": round(cost * (1 - COST_SPREAD)),
            "high": round(cost * (1 + COST_SPREAD)),
            "places": places,
            "source": SOURCE,
            "year": REFERENCE_YEAR,
            "run_id": run_id,
        }
        for (action, band), (cost, places) in UNIT_COSTS.items()
    ]
    conn.execute(
        text(
            "INSERT INTO unit_cost (action, band, cost_rwf, cost_low_rwf, cost_high_rwf, "
            "places_added, source, reference_year, origin, pipeline_run_id) VALUES (:action, "
            ":band, :cost, :low, :high, :places, :source, :year, 'simulated', :run_id)"
        ),
        rows,
    )
    return len(rows)


def _site_points(conn: Connection, sector: str, count: int, seed: int) -> list[tuple[float, float]]:
    rows = conn.execute(
        text(
            "SELECT ST_X(p), ST_Y(p) FROM ("
            "  SELECT ST_Transform(d.geom, 4326) AS p, d.path FROM admin_unit a,"
            "  ST_Dump(ST_GeneratePoints("
            "    ST_Buffer(ST_Transform(a.geom, 32735), -300), :n, :seed)) d"
            "  WHERE a.code = :code) s ORDER BY s.path"
        ),
        {"code": sector, "n": count, "seed": seed},
    ).all()
    return [(x, y) for x, y in rows]


CENTRES = text(
    """
    SELECT c.code, c.name, c.type, c.sector_code, ST_X(c.location) AS lon,
        ST_Y(c.location) AS lat
    FROM centre c JOIN admin_unit s ON s.code = c.sector_code
    WHERE s.parent_code = :d AND c.status = 'active' ORDER BY c.code
    """
)


def build_sites(conn: Connection) -> list[dict[str, Any]]:
    """Village and school sites (simulated) in every sector, plus an upgrade option for each
    home-based centre and a support option for every centre, simulated or loaded."""
    r = rng("sites")
    centres = [dict(row._mapping) for row in conn.execute(CENTRES, {"d": DEMO_DISTRICT})]
    sectors = conn.execute(
        text("SELECT code, name FROM admin_unit WHERE parent_code = :d ORDER BY code"),
        {"d": DEMO_DISTRICT},
    ).all()
    sites: list[dict[str, Any]] = []
    for index, sector in enumerate(sectors):
        has_school = index % 2 == 0
        points = _site_points(conn, sector.code, 3 if has_school else 2, seed=300 + index)
        short = sector.code.removeprefix("S-GICUMBI-")
        for n, (lon, lat) in enumerate(points[:2]):
            sites.append(
                {
                    "id": f"SITE-{short}-V{n + 1}",
                    "kind": CandidateKind.VILLAGE.value,
                    "name": f"{sector.name} village site {LETTERS[n]}",
                    "sector_code": sector.code,
                    "centre_code": None,
                    "lon": lon,
                    "lat": lat,
                    "band": STORY_SITE_BANDS.get(
                        f"SITE-{short}-V{n + 1}", r.choice([CostBand.MEDIUM, CostBand.HIGH])
                    ).value,
                }
            )
        if has_school:
            lon, lat = points[2]
            sites.append(
                {
                    "id": f"SITE-{short}-S1",
                    "kind": CandidateKind.SCHOOL.value,
                    "name": f"{sector.name} primary school site",
                    "sector_code": sector.code,
                    "centre_code": None,
                    "lon": lon,
                    "lat": lat,
                    "band": CostBand.LOW.value,
                }
            )
    for centre in centres:
        base = {
            "sector_code": centre["sector_code"],
            "centre_code": centre["code"],
            "lon": centre["lon"],
            "lat": centre["lat"],
        }
        if centre["type"] == "home_based":
            sites.append(
                base
                | {
                    "id": f"SITE-{centre['code']}-U",
                    "kind": CandidateKind.CENTRE_UPGRADE.value,
                    "name": centre["name"],
                    "band": r.choice([CostBand.LOW, CostBand.MEDIUM]).value,
                }
            )
        sites.append(
            base
            | {
                "id": f"SITE-{centre['code']}-Q",
                "kind": CandidateKind.CENTRE_SUPPORT.value,
                "name": centre["name"],
                "band": CostBand.LOW.value,
            }
        )
    return sites


def load_sites(conn: Connection, run_id: object) -> int:
    rows = build_sites(conn)
    conn.execute(
        text(
            "INSERT INTO candidate_site (id, kind, name, sector_code, centre_code, location, "
            "unit_cost_band, source, reference_year, origin, pipeline_run_id) VALUES (:id, :kind, "
            ":name, :sector_code, :centre_code, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), "
            ":band, :source, :year, 'simulated', :run_id)"
        ),
        [row | {"source": SOURCE, "year": REFERENCE_YEAR, "run_id": run_id} for row in rows],
    )
    return len(rows)
