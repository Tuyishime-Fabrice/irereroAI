"""Simulated need estimates with intervals: Gicumbi sectors in depth, other districts coarsely.

Gicumbi's stunting value is anchored to the RDHS 2025 district figure; sector values are
simulated around it so that their child-weighted mean equals the anchor. Child counts are not
anchored to any published figure and are labelled simulated; Phase 2 replaces them with PHC5.
"""

import random
from typing import Any

from sqlalchemy import Connection, text

from pipelines.demo.config import (
    DEMO_DISTRICT,
    GICUMBI_STUNTING,
    GICUMBI_STUNTING_SOURCE,
    REFERENCE_YEAR,
    SOURCE,
    TOWN_SECTOR,
    UNDERSERVED_SECTOR,
    rng,
    stable_id,
)

MODEL_VERSION = "need-simulated-1"
KIGALI = {"D-GASABO", "D-KICUKIRO", "D-NYARUGENGE"}
YOUNG_SHARE = 0.43  # share of children 0-6 who are 0-2
# Sectors with thin (simulated) survey coverage get wide intervals: the map hatches them.
WIDE_UNCERTAINTY = {UNDERSERVED_SECTOR, "S-GICUMBI-RUSHAKI", "S-GICUMBI-KANIGA"}


def _bounded(value: float, half_width: float, lo: float = 0.0, hi: float = 1.0) -> dict[str, float]:
    return {
        "estimate": round(value, 4),
        "low": round(max(lo, value - half_width), 4),
        "high": round(min(hi, value + half_width), 4),
    }


def _count(value: float, relative: float) -> dict[str, int]:
    return {
        "estimate": round(value),
        "low": round(value * (1 - relative)),
        "high": round(value * (1 + relative)),
    }


def _row(area: str, values: dict[str, Any], source: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": stable_id("need", area),
        "area_code": area,
        "model_version_id": MODEL_VERSION,
        "source": source,
        "reference_year": REFERENCE_YEAR,
        "origin": "simulated",
    }
    for measure, bounds in values.items():
        for part, value in bounds.items():
            row[f"{measure}_{part}"] = value
    return row


def _sector_rows(
    conn: Connection, r: random.Random
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Need rows per sector, and simulated poverty shares (the EICV7 stand-in)."""
    sectors = conn.execute(
        text("SELECT code, area_km2 FROM admin_unit WHERE parent_code = :d ORDER BY code"),
        {"d": DEMO_DISTRICT},
    ).all()
    children, stunting, barrier, poverty = [], [], [], []
    for s in sectors:
        density = r.uniform(55, 110) * (2.2 if s.code == TOWN_SECTOR else 1.0)
        children.append(density * s.area_km2)
        stunting.append(min(0.55, max(0.22, r.gauss(GICUMBI_STUNTING, 0.06))))
        barrier.append(r.uniform(0.2, 0.42) + (0.08 if s.code == TOWN_SECTOR else 0.0))
        poverty.append(r.uniform(0.15, 0.45))
    under = sectors.index(next(s for s in sectors if s.code == UNDERSERVED_SECTOR))
    stunting[under], poverty[under] = 0.49, 0.47
    # Rescale so the child-weighted mean equals the published district value exactly.
    weighted = sum(c * s for c, s in zip(children, stunting, strict=True)) / sum(children)
    stunting = [s * GICUMBI_STUNTING / weighted for s in stunting]

    rows = []
    for i, s in enumerate(sectors):
        wide = s.code in WIDE_UNCERTAINTY
        relative = r.uniform(0.22, 0.3) if wide else r.uniform(0.06, 0.14)
        values = {
            "children_0_2": _count(children[i] * YOUNG_SHARE, relative),
            "children_3_6": _count(children[i] * (1 - YOUNG_SHARE), relative),
            "stunting_risk": _bounded(
                stunting[i], r.uniform(0.1, 0.13) if wide else r.uniform(0.03, 0.06)
            ),
            "mothers_barrier_share": _bounded(barrier[i], r.uniform(0.04, 0.1)),
        }
        source = f"{SOURCE}; stunting: {GICUMBI_STUNTING_SOURCE}"
        rows.append(_row(s.code, values, source))
    return rows, {s.code: round(p, 4) for s, p in zip(sectors, poverty, strict=True)}


def _district_rows(
    conn: Connection, r: random.Random, sector_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    districts = conn.execute(
        text("SELECT code, area_km2 FROM admin_unit WHERE level = 'district' ORDER BY code")
    ).all()
    values = []
    for d in districts:
        if d.code == DEMO_DISTRICT:
            totals = {
                measure: {
                    part: sum(row[f"{measure}_{part}"] for row in sector_rows)
                    for part in ("estimate", "low", "high")
                }
                for measure in ("children_0_2", "children_3_6")
            }
            values.append(
                totals
                | {
                    "stunting_risk": {"estimate": GICUMBI_STUNTING, "low": 0.35, "high": 0.43},
                    "mothers_barrier_share": _bounded(r.uniform(0.28, 0.36), 0.05),
                }
            )
            continue
        density = r.uniform(60, 140) * (3.0 if d.code in KIGALI else 1.0)
        relative = r.uniform(0.08, 0.25)
        stunting = r.uniform(0.15, 0.42) * (0.6 if d.code in KIGALI else 1.0)
        values.append(
            {
                "children_0_2": _count(density * d.area_km2 * YOUNG_SHARE, relative),
                "children_3_6": _count(density * d.area_km2 * (1 - YOUNG_SHARE), relative),
                "stunting_risk": _bounded(stunting, r.uniform(0.03, 0.09)),
                "mothers_barrier_share": _bounded(r.uniform(0.2, 0.5), r.uniform(0.04, 0.1)),
            }
        )
    rows = []
    for i, d in enumerate(districts):
        source = SOURCE
        if d.code == DEMO_DISTRICT:
            source = f"{SOURCE}; stunting: RDHS 2025 district value 38.8% (interval simulated)"
        rows.append(_row(d.code, values[i], source))
    return rows


INSERT = text(
    """
    INSERT INTO need_estimate (id, area_code, model_version_id,
        children_0_2_estimate, children_0_2_low, children_0_2_high,
        children_3_6_estimate, children_3_6_low, children_3_6_high,
        stunting_risk_estimate, stunting_risk_low, stunting_risk_high,
        mothers_barrier_share_estimate, mothers_barrier_share_low, mothers_barrier_share_high,
        source, reference_year, origin, pipeline_run_id)
    VALUES (:id, :area_code, :model_version_id,
        :children_0_2_estimate, :children_0_2_low, :children_0_2_high,
        :children_3_6_estimate, :children_3_6_low, :children_3_6_high,
        :stunting_risk_estimate, :stunting_risk_low, :stunting_risk_high,
        :mothers_barrier_share_estimate, :mothers_barrier_share_low, :mothers_barrier_share_high,
:source, :reference_year, :origin, :run_id)
    """
)


POVERTY = text(
    "INSERT INTO area_indicator (id, area_code, indicator, value, unit, source, reference_year, "
    "origin, pipeline_run_id) VALUES (:id, :area, 'poverty_headcount', :value, 'share', "
    ":source, :year, 'simulated', :run_id)"
)


def load_need(conn: Connection, run_id: object) -> int:
    """Simulated need for every district and the pilot's sectors, and the pilot's simulated
    poverty shares. Loaded official values replace parts of it later in the build."""
    r = rng("need")
    sector_rows, poverty = _sector_rows(conn, r)
    rows = sector_rows + _district_rows(conn, r, sector_rows)
    conn.execute(INSERT, [row | {"run_id": run_id} for row in rows])
    conn.execute(
        POVERTY,
        [
            {
                "id": stable_id("poverty", area),
                "area": area,
                "value": value,
                "source": SOURCE,
                "year": REFERENCE_YEAR,
                "run_id": run_id,
            }
            for area, value in poverty.items()
        ],
    )
    return len(rows)
