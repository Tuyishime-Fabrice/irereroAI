"""Real boundaries: provinces, districts and sectors from geoBoundaries (CC BY 4.0).

These shapes are public data, not simulated, and are stored with origin = public. If the
download fails the generator stops: it never draws made-up geography.
"""

import json
import urllib.request
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, text

from irerero_contract.enums import AdminLevel, Origin, RunStatus
from pipelines.adapter import RAW_DIR, CheckResult, RunRecorder, file_fingerprint
from pipelines.demo.config import slug

BASE_URL = (
    "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/RWA"
)
LEVELS = {"ADM1": AdminLevel.PROVINCE, "ADM2": AdminLevel.DISTRICT, "ADM3": AdminLevel.SECTOR}
EXPECTED_COUNTS = {AdminLevel.PROVINCE: 5, AdminLevel.DISTRICT: 30, AdminLevel.SECTOR: 416}
SOURCE = "geoBoundaries gbOpen RWA (from NISR open data), CC BY 4.0"
REFERENCE_YEAR = 2023
RAW = RAW_DIR / "geoboundaries"


class BoundaryDownloadError(RuntimeError):
    pass


def download() -> list[Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    paths = []
    for adm in LEVELS:
        path = RAW / f"geoBoundaries-RWA-{adm}_simplified.geojson"
        if not path.exists():
            url = f"{BASE_URL}/{adm}/{path.name}"
            try:
                with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
                    path.write_bytes(response.read())
            except OSError as error:
                raise BoundaryDownloadError(
                    f"Could not download {url}: {error}. The demo needs real boundaries and "
                    "will not invent them. Download the file into data/raw/geoboundaries/ "
                    "by hand, or allow the host in your network policy."
                ) from error
        paths.append(path)
    return paths


def _stage(conn: Connection, paths: list[Path]) -> None:
    conn.execute(
        text(
            "CREATE TEMP TABLE gb_stage (adm text, name text, shape_id text, "
            "geom geometry(MultiPolygon, 4326)) ON COMMIT DROP"
        )
    )
    rows = []
    for adm, path in zip(LEVELS, paths, strict=True):
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            props = feature["properties"]
            rows.append(
                {
                    "adm": adm,
                    "name": props["shapeName"],
                    "shape_id": props["shapeID"],
                    "geojson": json.dumps(feature["geometry"]),
                }
            )
    conn.execute(
        text(
            "INSERT INTO gb_stage SELECT :adm, :name, :shape_id, "
            "ST_Multi(ST_CollectionExtract(ST_MakeValid("
            "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)), 3))"
        ),
        rows,
    )


def _parents(conn: Connection, child: str, parent: str) -> dict[str, list[str]]:
    """shape_id of each child unit -> names of the parent units containing its interior point."""
    result: dict[str, list[str]] = {}
    for shape_id, parent_name in conn.execute(
        text(
            "SELECT c.shape_id, p.name FROM gb_stage c JOIN gb_stage p "
            "ON p.adm = :parent AND ST_Contains(p.geom, ST_PointOnSurface(c.geom)) "
            "WHERE c.adm = :child"
        ),
        {"child": child, "parent": parent},
    ):
        result.setdefault(shape_id, []).append(parent_name)
    return result


def _province_code(name: str) -> str:
    return "P-" + slug(name.removesuffix(" Province"))


def _units(conn: Connection) -> tuple[list[dict[str, Any]], list[CheckResult]]:
    names = {
        shape_id: (adm, name)
        for adm, name, shape_id in conn.execute(text("SELECT adm, name, shape_id FROM gb_stage"))
    }
    district_parents = _parents(conn, "ADM2", "ADM1")
    sector_parents = _parents(conn, "ADM3", "ADM2")
    units = [{"shape_id": None, "code": "RW", "name": "Rwanda", "level": "country", "parent": None}]
    for shape_id, (adm, name) in sorted(names.items(), key=lambda item: (item[1][0], item[1][1])):
        if adm == "ADM1":
            units.append(
                {"code": _province_code(name), "name": name, "level": "province", "parent": "RW"}
                | {"shape_id": shape_id}
            )
        elif adm == "ADM2" and len(district_parents.get(shape_id, [])) == 1:
            units.append(
                {
                    "shape_id": shape_id,
                    "code": f"D-{slug(name)}",
                    "name": name,
                    "level": "district",
                    "parent": _province_code(district_parents[shape_id][0]),
                }
            )
        elif adm == "ADM3" and len(sector_parents.get(shape_id, [])) == 1:
            district = sector_parents[shape_id][0]
            units.append(
                {
                    "shape_id": shape_id,
                    "code": f"S-{slug(district)}-{slug(name)}",
                    "name": name,
                    "level": "sector",
                    "parent": f"D-{slug(district)}",
                }
            )
    counts = {level: sum(u["level"] == level.value for u in units) for level in EXPECTED_COUNTS}
    codes = [u["code"] for u in units]
    checks = [
        CheckResult(
            f"{level.value}_count",
            counts[level] == expected,
            f"{counts[level]} {level.value} units with exactly one parent, expected {expected}",
        )
        for level, expected in EXPECTED_COUNTS.items()
    ]
    checks.append(CheckResult("unique_codes", len(codes) == len(set(codes)), "codes are unique"))
    gicumbi = sum(u["parent"] == "D-GICUMBI" for u in units)
    checks.append(CheckResult("gicumbi_sectors", gicumbi == 21, f"Gicumbi has {gicumbi} sectors"))
    return units, checks


INSERT_UNIT = text(
    """
    INSERT INTO admin_unit (code, name, level, parent_code, source_ref, geom, geom_medium,
        geom_coarse, centroid, area_km2, source, reference_year, origin, pipeline_run_id)
    SELECT :code, :name, :level, :parent, :shape_id, g.geom,
        ST_Multi(ST_Transform(ST_SimplifyPreserveTopology(ST_Transform(g.geom, 32735), 50), 4326)),
        ST_Multi(ST_Transform(ST_SimplifyPreserveTopology(ST_Transform(g.geom, 32735), 500), 4326)),
        ST_PointOnSurface(g.geom), ST_Area(ST_Transform(g.geom, 32735)) / 1e6,
        :source, :year, :origin, :run_id
    FROM (
        SELECT CASE WHEN CAST(:shape_id AS text) IS NULL
            THEN (SELECT ST_Multi(ST_Union(geom)) FROM gb_stage WHERE adm = 'ADM1')
            ELSE (SELECT geom FROM gb_stage WHERE shape_id = CAST(:shape_id AS text))
        END AS geom
    ) g
    """
)


def load_boundaries(engine: Engine) -> int:
    """Download if needed, check and load admin units. Returns the number of units."""
    paths = download()
    recorder = RunRecorder(engine, "geoboundaries", Origin.PUBLIC)
    run_id = recorder.start([file_fingerprint(p) for p in paths])
    with engine.begin() as conn:
        _stage(conn, paths)
        units, checks = _units(conn)
        if not all(c.passed for c in checks):
            recorder.finish(RunStatus.FAILED, {}, checks)
            failed = "; ".join(c.detail for c in checks if not c.passed)
            raise RuntimeError(f"Boundary checks failed: {failed}")
        meta = {"source": SOURCE, "year": REFERENCE_YEAR, "origin": Origin.PUBLIC.value}
        for level in ("country", "province", "district", "sector"):
            rows = [u | meta | {"run_id": run_id} for u in units if u["level"] == level]
            conn.execute(INSERT_UNIT, rows)
        empty = conn.execute(
            text("SELECT count(*) FROM admin_unit WHERE ST_IsEmpty(geom_coarse)")
        ).scalar_one()
        checks.append(CheckResult("simplified_not_empty", empty == 0, f"{empty} empty shapes"))
    recorder.finish(RunStatus.SUCCEEDED, {"admin_unit": len(units)}, checks)
    return len(units)
