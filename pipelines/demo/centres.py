"""Simulated ECD centres for Gicumbi: the story centres plus generated ones in every sector."""

from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import CentreType, FeeBand
from pipelines.demo.config import (
    DEMO_DISTRICT,
    ENROLMENT_AS_OF,
    REFERENCE_YEAR,
    SOURCE,
    UNDERSERVED_SECTOR,
    rng,
)
from pipelines.demo.story import STORY_BY_CODE, STORY_CENTRES

CAPACITY = {
    CentreType.HOME_BASED: (15, 30),
    CentreType.COMMUNITY_BASED: (40, 80),
    CentreType.SCHOOL_BASED: (40, 100),
    CentreType.CENTRE_BASED: (60, 120),
}
HOURS = {
    CentreType.HOME_BASED: "Mo-Fr 07:30-12:00",
    CentreType.COMMUNITY_BASED: "Mo-Fr 07:30-15:00",
    CentreType.SCHOOL_BASED: "Mo-Fr 07:00-12:30",
    CentreType.CENTRE_BASED: "Mo-Sa 07:00-17:00",
}
FEES = {
    CentreType.HOME_BASED: (FeeBand.FREE, FeeBand.UNDER_1000),
    CentreType.COMMUNITY_BASED: (FeeBand.UNDER_1000, FeeBand.FROM_1000_TO_5000),
    CentreType.SCHOOL_BASED: (FeeBand.FROM_1000_TO_5000,),
    CentreType.CENTRE_BASED: (FeeBand.FROM_1000_TO_5000, FeeBand.OVER_5000),
}
TYPE_WEIGHTS = {
    CentreType.HOME_BASED: 0.4,
    CentreType.COMMUNITY_BASED: 0.3,
    CentreType.SCHOOL_BASED: 0.2,
    CentreType.CENTRE_BASED: 0.1,
}
NAME_PATTERN = {
    CentreType.HOME_BASED: "Urugo mbonezamikurire {sector} {n}",
    CentreType.COMMUNITY_BASED: "Irerero {sector} {n}",
    CentreType.SCHOOL_BASED: "Irerero ry'ishuri {sector} {n}",
    CentreType.CENTRE_BASED: "Ikigo cy'irerero {sector} {n}",
}
# Byumba is the district town and gets more centres; the under-served sector gets no new ones.
EXTRA_CENTRES = {"S-GICUMBI-BYUMBA": 3, UNDERSERVED_SECTOR: 0}
# Generated centres enrol between these shares of their capacity.
ENROLMENT_SHARE = (0.6, 1.05)


def _sectors(conn: Connection) -> list[tuple[str, str]]:
    return [
        (row.code, row.name)
        for row in conn.execute(
            text("SELECT code, name FROM admin_unit WHERE parent_code = :d ORDER BY code"),
            {"d": DEMO_DISTRICT},
        )
    ]


def _points(conn: Connection, sector_code: str, count: int, seed: int) -> list[tuple[float, float]]:
    """Seeded random points at least 150 m inside the sector boundary."""
    rows = conn.execute(
        text(
            "SELECT ST_X(p), ST_Y(p) FROM ("
            "  SELECT ST_Transform(d.geom, 4326) AS p, d.path FROM admin_unit a,"
            "  ST_Dump(ST_GeneratePoints("
            "    ST_Buffer(ST_Transform(a.geom, 32735), -150), :n, :seed)) d"
            "  WHERE a.code = :code) s ORDER BY s.path"
        ),
        {"code": sector_code, "n": count, "seed": seed},
    ).all()
    return [(x, y) for x, y in rows]


def build_centres(conn: Connection) -> list[dict[str, Any]]:
    """Return centre rows. Story centres keep their fixed codes; others are numbered after them."""
    r = rng("centres")
    sectors = _sectors(conn)
    planned: list[dict[str, Any]] = [
        {
            "code": c.code,
            "name": c.name,
            "type": c.type,
            "sector_code": c.sector_code,
            "capacity": c.capacity,
        }
        for c in STORY_CENTRES
    ]
    number = len(planned)
    for sector_code, sector_name in sectors:
        extra = EXTRA_CENTRES.get(sector_code, r.randint(1, 3))
        for n in range(1, extra + 1):
            kind = r.choices(list(TYPE_WEIGHTS), weights=list(TYPE_WEIGHTS.values()))[0]
            number += 1
            planned.append(
                {
                    "code": f"ECD-GIC-{number:03d}",
                    "name": NAME_PATTERN[kind].format(sector=sector_name, n=n),
                    "type": kind,
                    "sector_code": sector_code,
                    "capacity": r.randint(*CAPACITY[kind]),
                }
            )

    by_sector: dict[str, list[dict[str, Any]]] = {}
    for centre in planned:
        by_sector.setdefault(centre["sector_code"], []).append(centre)
    for sector_index, (sector_code, centres) in enumerate(sorted(by_sector.items())):
        points = _points(conn, sector_code, len(centres), seed=7 + sector_index)
        for centre, (lon, lat) in zip(centres, points, strict=True):
            centre["lon"], centre["lat"] = lon, lat

    rows = []
    for centre in planned:
        kind = centre["type"]
        story = STORY_BY_CODE.get(centre["code"])
        enrolment = (
            story.enrolment if story else round(centre["capacity"] * r.uniform(*ENROLMENT_SHARE))
        )
        rows.append(
            {
                "code": centre["code"],
                "name": centre["name"],
                "type": kind.value,
                "status": "active",
                "sector_code": centre["sector_code"],
                "lon": centre["lon"],
                "lat": centre["lat"],
                "capacity": centre["capacity"],
                "serves_0_2": kind is not CentreType.SCHOOL_BASED,
                "serves_3_6": True,
                "opening_hours": HOURS[kind],
                "fee_band": r.choice(FEES[kind]).value,
                "offers_meals": r.random() < 0.7,
                "offers_growth_monitoring": r.random() < 0.6,
                "disability_inclusive": r.random() < 0.25,
                "verified": story is not None or r.random() < 0.75,
                "water_available": story.water_available if story else r.random() < 0.85,
                "enrolment": enrolment,
                "enrolment_as_of": ENROLMENT_AS_OF,
            }
        )
    # The story needs these centres to have the services their problems are about.
    for row in rows:
        if row["code"] in {"ECD-GIC-001", "ECD-GIC-002", "ECD-GIC-003"}:
            row["offers_meals"] = True
    return rows


INSERT_CENTRE = text(
    """
    INSERT INTO centre (code, name, type, status, sector_code, location, capacity, serves_0_2,
        serves_3_6, opening_hours, fee_band, offers_meals, offers_growth_monitoring,
        disability_inclusive, verified, water_available, enrolment, enrolment_as_of, source,
        reference_year, origin, pipeline_run_id)
    VALUES (:code, :name, :type, :status, :sector_code,
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :capacity, :serves_0_2, :serves_3_6,
        :opening_hours, :fee_band, :offers_meals, :offers_growth_monitoring,
        :disability_inclusive, :verified, :water_available, :enrolment, :enrolment_as_of,
        :source, :year, 'simulated', :run_id)
    """
)


def load_centres(conn: Connection, run_id: object) -> list[dict[str, Any]]:
    rows = build_centres(conn)
    conn.execute(
        INSERT_CENTRE,
        [row | {"source": SOURCE, "year": REFERENCE_YEAR, "run_id": run_id} for row in rows],
    )
    return rows
