"""Simulated parent demand: empty searches and centre requests, clustered where centres are few.

Locations go through the same 500 m grid snapping as live requests from the Find page.
"""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import Connection, insert, text

from irerero_contract.grid import cell_centre, cell_id, nearest_sector
from irerero_contract.tables import DemandSignal
from pipelines.demo.config import DEMO_DISTRICT, UNDERSERVED_SECTOR, WEEKS, rng, stable_id

CLUSTER_SIGNALS = 14
SCATTERED_SIGNALS = 4


def _random_points(conn: Connection, area_sql: str, n: int, seed: int) -> list[tuple[float, float]]:
    rows = conn.execute(
        text(
            # area_sql is one of the two constant queries below, never user input.
            "SELECT ST_X(d.geom), ST_Y(d.geom) FROM "  # noqa: S608
            f"ST_Dump(ST_GeneratePoints(({area_sql}), :n, :seed)) d ORDER BY d.path"
        ),
        {"n": n, "seed": seed, "sector": UNDERSERVED_SECTOR, "district": DEMO_DISTRICT},
    ).all()
    return [(x, y) for x, y in rows]


def load_demand(conn: Connection) -> int:
    r = rng("demand")
    # The cluster sits in the northern half of the under-served sector, so it reads as one area.
    cluster = _random_points(
        conn,
        "SELECT ST_Intersection(geom, ST_Translate(ST_Envelope(geom), 0, "
        "(ST_YMax(geom) - ST_YMin(geom)) / 2)) FROM admin_unit WHERE code = :sector",
        CLUSTER_SIGNALS,
        seed=41,
    )
    scattered = _random_points(
        conn,
        "SELECT ST_Union(geom) FROM admin_unit WHERE parent_code = :district AND code <> :sector",
        SCATTERED_SIGNALS,
        seed=42,
    )
    count = 0
    for n, (lon, lat) in enumerate(cluster + scattered):
        week = WEEKS[r.randint(5, len(WEEKS) - 1)]
        created = datetime.combine(week + timedelta(days=r.randint(0, 6)), time(8), tzinfo=UTC)
        sector = conn.execute(nearest_sector(cell_centre(lon, lat))).scalar_one()
        conn.execute(
            insert(DemandSignal).values(
                id=stable_id("demand", n),
                kind="centre_request" if n % 3 == 0 else "empty_search",
                grid_cell=cell_id(lon, lat),
                cell_centre=cell_centre(lon, lat),
                sector_code=sector,
                age_band=r.choice(["0_2", "3_6"]),
                origin="simulated",
                created_at=created + timedelta(minutes=r.randint(0, 600)),
            )
        )
        count += 1
    return count
