"""MINEDUC school locations for the distance layer (provisional while the list is partial).

The file is the MINEDUC school register exported as GeoJSON points. The copy received holds
only the 139 schools of category PRE_PRIMARY (standalone nursery schools); most pre-primary
classes are inside primary schools, which it does not list. Every result built on it is
therefore labelled provisional: a child far from a *listed* school may still be near a school
that is not in the file, so the share beyond 1 km is an upper bound, never proof that an area
has no school nearby.

Records are read one by one: a record with no usable point (missing or malformed geometry,
coordinates outside Rwanda, swapped longitude and latitude) is counted and left out, never
guessed. Missing properties are counted per property.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from irerero.config import PROVISIONAL, RAW
from irerero.data.spec import COORDINATE_RANGE, Column, Dataset

FILE = "schools.geojson"
DATASET = Dataset(
    key="schools",
    title="MINEDUC school locations (provisional: standalone pre-primary schools only)",
    publisher="Ministry of Education (MINEDUC), school register",
    files=(FILE,),
    format="GeoJSON points, EPSG:4326 (the register's export)",
    columns=(
        Column("school_code", "text", "MINEDUC school code"),
        Column("school_name", "text", "School name", required=False),
        Column("district", "text", "District", required=False),
        Column("sector", "text", "Sector", required=False),
        Column("school_category", "text", "Category (PRE_PRIMARY in this copy)", required=False),
        Column("preprimary_students_total", "integer", "Pre-primary pupils", required=False),
    ),
    level="school points",
    reference_period="register export (date not stated)",
    licence="MINEDUC data; cite MINEDUC",
    url=None,
    used_by=(
        "PLAN: share of children more than 1 km from a listed school (provisional upper bound)",
        "Overview map: school locations",
    ),
    status=PROVISIONAL,
    fallback="Simulated school points (or OpenStreetMap when its extract is loaded)",
    notes=(
        "Fetched from the team's private repository on first start when IRERERO_SCHOOLS_PATH "
        "is set (see docs/deploy_private_data.md), or put in data/raw/schools/schools.geojson.",
        "Partial list: the distance results are provisional and are not used as evidence in "
        "the bottleneck rules.",
    ),
)
PROPERTIES = (
    "school_code",
    "school_name",
    "district",
    "sector",
    "school_category",
    "school_status",
    "preprimary_students_total",
)
SOURCE = "mineduc_provisional"


@dataclass
class Report:
    """What the loader found, for the build log, the Data & methods page and the tests."""

    features: int = 0
    loaded: int = 0
    invalid_coordinates: int = 0
    missing_geometry: int = 0
    duplicate_points: int = 0
    missing_properties: dict[str, int] = field(default_factory=dict)
    categories: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "features": self.features,
            "loaded": self.loaded,
            "invalid_coordinates": self.invalid_coordinates,
            "missing_geometry": self.missing_geometry,
            "duplicate_points": self.duplicate_points,
            "missing_properties": self.missing_properties,
            "categories": self.categories,
            "errors": self.errors,
        }


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _inside(lon: float, lat: float) -> bool:
    (lon_lo, lon_hi), (lat_lo, lat_hi) = COORDINATE_RANGE["longitude"], COORDINATE_RANGE["latitude"]
    return lon_lo <= lon <= lon_hi and lat_lo <= lat <= lat_hi


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def parse(data: dict) -> tuple[pd.DataFrame, Report]:
    """(schools with school_id, lon, lat and the properties above, report)."""
    report = Report()
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        report.errors.append("not a GeoJSON FeatureCollection")
        return pd.DataFrame(columns=["school_id", "lon", "lat", *PROPERTIES]), report
    rows = []
    report.missing_properties = dict.fromkeys(PROPERTIES, 0)
    for i, feature in enumerate(data["features"]):
        report.features += 1
        if not isinstance(feature, dict):
            report.errors.append(f"record {i + 1} is not a GeoJSON feature")
            continue
        props = feature.get("properties") or {}
        for name in PROPERTIES:
            if _blank(props.get(name)):
                report.missing_properties[name] += 1
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") if geometry.get("type") == "Point" else None
        if not isinstance(coords, list | tuple) or len(coords) < 2:
            report.missing_geometry += 1
            continue
        lon, lat = _number(coords[0]), _number(coords[1])
        if lon is None or lat is None or not _inside(lon, lat):
            report.invalid_coordinates += 1  # includes swapped lon/lat: never swapped back
            continue
        category = str(props.get("school_category") or "not stated")
        report.categories[category] = report.categories.get(category, 0) + 1
        code = props.get("school_code")
        rows.append(
            {
                "school_id": f"mineduc-{code}" if not _blank(code) else f"mineduc-row{i + 1}",
                "lon": lon,
                "lat": lat,
                **{name: props.get(name) for name in PROPERTIES},
            }
        )
    frame = pd.DataFrame(rows, columns=["school_id", "lon", "lat", *PROPERTIES])
    frame["preprimary_students_total"] = pd.to_numeric(
        frame.preprimary_students_total, errors="coerce"
    ).astype("Int64")
    report.loaded = len(frame)
    report.duplicate_points = int(frame.duplicated(["lon", "lat"]).sum())
    return frame, report


def read(path: Path) -> tuple[pd.DataFrame, Report]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        report = Report(errors=[f"{path.name} could not be read as JSON: {error}"])
        return pd.DataFrame(columns=["school_id", "lon", "lat", *PROPERTIES]), report
    return parse(data)


def load(raw: Path = RAW) -> tuple[pd.DataFrame, Report] | None:
    """The staged school list, or None while there is none."""
    if not DATASET.present(raw):
        return None
    return read(DATASET.folder(raw) / FILE)
