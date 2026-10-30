"""Administrative boundaries, province to sector."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from irerero.config import DEMO, OBSERVED, RAW, REFERENCE
from irerero.data.spec import Column, Dataset
from irerero.data.validate import SchemaError

LEVELS = ("province", "district", "sector")
DATASET = Dataset(
    key="boundaries",
    title="Administrative boundaries, province to sector (COD-AB)",
    publisher="NISR via the Humanitarian Data Exchange",
    files=("provinces.geojson", "districts.geojson", "sectors.geojson"),
    format="GeoJSON, EPSG:4326",
    columns=(
        Column("nisr_code", "text", "Official NISR code of the unit"),
        Column("name", "text", "Official name"),
        Column("parent_nisr_code", "text", "NISR code of the unit one level up", required=False),
    ),
    level="province, district, sector",
    reference_period="2022",
    licence="CC BY 4.0",
    url="https://data.humdata.org/dataset/cod-ab-rwa",
    used_by=("every map", "the join to NISR sector codes"),
    status=OBSERVED,
    fallback=(
        "geoBoundaries gbOpen RWA (CC BY 4.0, from NISR open data), simplified; real shapes, "
        "no NISR codes"
    ),
    notes=(
        "Rename the COD-AB columns to nisr_code, name and parent_nisr_code. Each nisr_code "
        "must be in the reviewed crosswalks (nisr_sector_code, nisr_district_code).",
    ),
)
GEOBOUNDARIES = "geoboundaries"
# Provinces by NISR code, with the ids and names the rest of the app uses.
PROVINCES = {
    "RW1": ("P-CITY-OF-KIGALI", "City of Kigali"),
    "RW2": ("P-SOUTHERN", "Southern Province"),
    "RW3": ("P-WESTERN", "Western Province"),
    "RW4": ("P-NORTHERN", "Northern Province"),
    "RW5": ("P-EASTERN", "Eastern Province"),
}


def _codes(file: str, column: str) -> dict[str, str]:
    frame = pd.read_csv(REFERENCE / file, dtype=str).fillna("")
    return {code: geo for code, geo in zip(frame[column], frame.geo_id, strict=True) if code}


def _ids_to_codes(file: str, column: str) -> dict[str, str]:
    frame = pd.read_csv(REFERENCE / file, dtype=str).fillna("")
    rows = frame[(frame.source == "*") & (frame[column] != "")]
    return dict(zip(rows.geo_id, rows[column], strict=True))


def load(raw: Path = RAW) -> tuple[dict[str, gpd.GeoDataFrame], str, bool]:
    """({level: frame with geo_id, name, parent_id, nisr_code, geometry}, source_id, real)."""
    if not DATASET.present(raw):
        # geoBoundaries shapes carry no codes; the crosswalks give each unit its NISR code.
        codes = {
            "sector": _ids_to_codes("sector_name_crosswalk.csv", "nisr_sector_code"),
            "district": _ids_to_codes("district_name_crosswalk.csv", "nisr_district_code"),
        }
        frames = {}
        for level in LEVELS:
            frame = gpd.read_file(DEMO / "boundaries" / f"{level}s.geojson")
            frame["nisr_code"] = frame.geo_id.map(codes.get(level, {}))
            frames[level] = frame
        return frames, GEOBOUNDARIES, False
    sectors = _codes("sector_name_crosswalk.csv", "nisr_sector_code")
    districts = _codes("district_name_crosswalk.csv", "nisr_district_code")
    frames = {}
    for level in LEVELS:
        frame = gpd.read_file(DATASET.folder(raw) / f"{level}s.geojson").to_crs(4326)
        if level == "province":
            unknown = sorted(set(frame.nisr_code) - set(PROVINCES))
            if unknown:
                raise SchemaError(f"provinces.geojson: unknown province codes {unknown}")
            frame["geo_id"] = frame.nisr_code.map(lambda c: PROVINCES[c][0])
            frame["name"] = frame.nisr_code.map(lambda c: PROVINCES[c][1])
            frame["parent_id"] = "RW"
        else:
            lookup = sectors if level == "sector" else districts
            frame["geo_id"] = frame.nisr_code.map(lookup)
            missing = frame.loc[frame.geo_id.isna(), "nisr_code"].tolist()
            if missing:
                raise SchemaError(
                    f"{level}s.geojson: NISR codes not in the reviewed crosswalk: {missing[:10]}"
                )
            parents = districts if level == "sector" else None
            frame["parent_id"] = (
                frame.parent_nisr_code.map(parents)
                if parents is not None
                else frame.parent_nisr_code.map(
                    dict(zip(frames["province"].nisr_code, frames["province"].geo_id, strict=True))
                )
            )
        frames[level] = frame[["geo_id", "name", "parent_id", "nisr_code", "geometry"]]
    return frames, DATASET.key, True
