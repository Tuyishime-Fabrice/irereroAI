"""Administrative boundaries, province to village, joined on official NISR codes.

With the official files in data/raw/boundaries/, units carry their NISR code. Otherwise the
build uses geoBoundaries (CC BY 4.0, from NISR open data; provinces, districts and sectors,
without official codes), stored as public data. If neither is available the build stops: it
never draws made-up geography.

Internal codes stay the same either way (D-GICUMBI, S-GICUMBI-BYUMBA), so saved plans and
decisions survive the switch to official boundaries.
"""

import json
import urllib.request
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, text

from irerero_contract.enums import AdminLevel, Origin, RunStatus
from pipelines.demo.config import slug
from pipelines.runs import RAW_DIR, CheckResult, RunRecorder, file_fingerprint
from pipelines.sources.readers import SchemaError, read_geojson
from pipelines.sources.spec import Column, Dataset, ExpectedFile

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


STAGE_TABLE = text(
    "CREATE TEMP TABLE gb_stage (adm text, name text, shape_id text, parent_id text, "
    "geom geometry(MultiPolygon, 4326)) ON COMMIT DROP"
)
STAGE_ROW = text(
    "INSERT INTO gb_stage SELECT :adm, :name, :shape_id, :parent_id, "
    "ST_Multi(ST_CollectionExtract(ST_MakeValid("
    "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)), 3))"
)


def _stage(conn: Connection, paths: list[Path]) -> None:
    conn.execute(STAGE_TABLE)
    rows = []
    for adm, path in zip(LEVELS, paths, strict=True):
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            props = feature["properties"]
            rows.append(
                {
                    "adm": adm,
                    "name": props["shapeName"],
                    "shape_id": props["shapeID"],
                    "parent_id": None,
                    "geojson": json.dumps(feature["geometry"]),
                }
            )
    conn.execute(STAGE_ROW, rows)


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
    for unit in units:
        unit["nisr"] = None
    return units, _checks(units)


def _checks(units: list[dict[str, Any]]) -> list[CheckResult]:
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
    return checks


INSERT_UNIT = text(
    """
    INSERT INTO admin_unit (code, name, level, parent_code, nisr_code, source_ref, geom,
        geom_medium, geom_coarse, centroid, area_km2, source, reference_year, origin,
        pipeline_run_id)
    SELECT :code, :name, :level, :parent, :nisr, :shape_id, g.geom,
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


OFFICIAL_LEVELS = {
    "ADM1": ("provinces.geojson", AdminLevel.PROVINCE),
    "ADM2": ("districts.geojson", AdminLevel.DISTRICT),
    "ADM3": ("sectors.geojson", AdminLevel.SECTOR),
    "ADM4": ("cells.geojson", AdminLevel.CELL),
    "ADM5": ("villages.geojson", AdminLevel.VILLAGE),
}
REQUIRED_OFFICIAL = ("ADM1", "ADM2", "ADM3")
OFFICIAL_COLUMNS = (
    Column("admin_code", "text", "Official NISR code"),
    Column("admin_name", "text", "Official name"),
    Column("parent_code", "text", "NISR code of the unit one level up", required=False),
)
OFFICIAL = Dataset(
    key="boundaries",
    title="Official administrative boundaries, province to village",
    publisher="NISR, via the Humanitarian Data Exchange (COD-AB)",
    access="Open download",
    url="https://data.humdata.org/dataset/cod-ab-rwa",
    licence="CC BY 4.0",
    origin=Origin.OFFICIAL,
    reference_year=2022,
    files=tuple(
        ExpectedFile(
            name, "geojson", f"{level.value.title()} polygons", required=adm in REQUIRED_OFFICIAL
        )
        for adm, (name, level) in OFFICIAL_LEVELS.items()
    ),
    columns=OFFICIAL_COLUMNS,
    level="village",
    joins_on="admin_code is the key every other dataset joins on",
    used_by=("every map", "every area dataset (join key)", "need model", "catchments"),
    produces=("admin_unit (with nisr_code)",),
    fallback=(
        "geoBoundaries provinces, districts and sectors (public, CC BY 4.0), without official "
        "codes; area files then join on admin_name"
    ),
    notes=(
        "Rename the COD-AB columns to admin_code, admin_name and parent_code, and export "
        "each level as GeoJSON in EPSG:4326. Cells and villages are optional.",
    ),
)


def _official_paths(raw: Path) -> dict[str, Path]:
    folder = raw / OFFICIAL.key
    return {
        adm: folder / name
        for adm, (name, _) in OFFICIAL_LEVELS.items()
        if (folder / name).is_file()
    }


def _stage_official(conn: Connection, paths: dict[str, Path]) -> list[dict[str, Any]]:
    conn.execute(STAGE_TABLE)
    staged = []
    for adm, path in paths.items():
        for feature in read_geojson(path, OFFICIAL_COLUMNS):
            props = feature.properties
            if adm != "ADM1" and not props["parent_code"]:
                raise SchemaError(f"{path.name}: {props['admin_code']} has no parent_code")
            staged.append(
                {
                    "adm": adm,
                    "name": props["admin_name"],
                    "shape_id": props["admin_code"],
                    "parent_id": props["parent_code"],
                    "geojson": json.dumps(feature.geometry),
                }
            )
    conn.execute(STAGE_ROW, staged)
    return staged


def _official_units(staged: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Internal codes from names for provinces to sectors (as with geoBoundaries), from the
    official code for cells and villages."""
    by_id = {s["shape_id"]: s for s in staged}
    codes: dict[str, str] = {}

    def code(row: dict[str, Any]) -> str:
        if row["shape_id"] in codes:
            return codes[row["shape_id"]]
        adm, name = row["adm"], row["name"]
        parent = by_id.get(row["parent_id"]) if row["parent_id"] else None
        if adm != "ADM1" and parent is None:
            raise SchemaError(f"{name}: parent_code {row['parent_id']} is not in the files")
        if adm == "ADM1":
            value = _province_code(name)
        elif adm == "ADM2":
            value = f"D-{slug(name)}"
        elif adm == "ADM3":
            assert parent is not None
            value = f"S-{slug(parent['name'])}-{slug(name)}"
        else:
            value = f"{'C' if adm == 'ADM4' else 'V'}-{row['shape_id']}"
        codes[row["shape_id"]] = value
        return value

    units = [
        {"shape_id": None, "code": "RW", "name": "Rwanda", "level": "country", "parent": None}
        | {"nisr": None}
    ]
    for row in staged:
        parent = by_id.get(row["parent_id"]) if row["parent_id"] else None
        units.append(
            {
                "shape_id": row["shape_id"],
                "code": code(row),
                "name": row["name"],
                "level": OFFICIAL_LEVELS[row["adm"]][1].value,
                "parent": code(parent) if parent else "RW",
                "nisr": row["shape_id"],
            }
        )
    return units


def load_boundaries(engine: Engine, raw: Path = RAW_DIR) -> tuple[int, Origin]:
    """Official boundaries if present, otherwise geoBoundaries. Returns (units, origin)."""
    official = OFFICIAL.present(raw)
    paths = list(_official_paths(raw).values()) if official else download()
    origin = Origin.OFFICIAL if official else Origin.PUBLIC
    source, year = (
        (OFFICIAL.title, OFFICIAL.reference_year) if official else (SOURCE, REFERENCE_YEAR)
    )
    recorder = RunRecorder(engine, OFFICIAL.key if official else "geoboundaries", origin)
    run_id = recorder.start([file_fingerprint(p) for p in paths])
    try:
        with engine.begin() as conn:
            if official:
                units = _official_units(_stage_official(conn, _official_paths(raw)))
                checks = _checks(units)
            else:
                _stage(conn, paths)
                units, checks = _units(conn)
            if not all(c.passed for c in checks):
                failed = "; ".join(c.detail for c in checks if not c.passed)
                raise SchemaError(f"Boundary checks failed: {failed}")
            meta = {"source": source, "year": year, "origin": origin.value, "run_id": run_id}
            for level in ("country", "province", "district", "sector", "cell", "village"):
                rows = [u | meta for u in units if u["level"] == level]
                if rows:
                    conn.execute(INSERT_UNIT, rows)
            empty = conn.execute(
                text("SELECT count(*) FROM admin_unit WHERE ST_IsEmpty(geom_coarse)")
            ).scalar_one()
            checks.append(CheckResult("simplified_not_empty", empty == 0, f"{empty} empty shapes"))
    except Exception:
        recorder.finish(RunStatus.FAILED, {}, [])
        raise
    recorder.finish(RunStatus.SUCCEEDED, {"admin_unit": len(units)}, checks)
    return len(units), origin
