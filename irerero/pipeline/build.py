"""Rebuild every analysis table from the files in data/raw/, demo data where missing.

    make data        (python -m irerero.pipeline.build)

Writes Parquet and simplified GeoJSON to data/processed/ and replaces the analysis tables in
the database. Plans, LEARN progress and the audit log are kept.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine

from irerero.config import PROCESSED, RAW
from irerero.data.registry import FILE_DATASETS
from irerero.data.sources import osm
from irerero.data.sources import schools as schools_source
from irerero.data.sources.boundaries import GEOBOUNDARIES
from irerero.data.validate import SchemaError
from irerero.db.session import engine as default_engine
from irerero.db.store import replace_analysis
from irerero.learn import content
from irerero.pipeline import diagnose_step
from irerero.pipeline.inputs import Inputs, load_inputs
from irerero.pipeline.observations import build_observations
from irerero.plan.distance import far_shares
from irerero.plan.estimate import estimate
from irerero.track import forecast

SIMPLIFY_DEGREES = 0.0014
PARQUET = (
    "geo_unit",
    "source",
    "observation",
    "estimate_2026",
    "model_output",
    "diagnosis",
    "forecast",
)


def geo_units(inputs: Inputs) -> pd.DataFrame:
    provinces = inputs.units["province"].set_index("geo_id").name
    districts = inputs.districts.set_index("geo_id")
    frames = [pd.DataFrame([{"geo_id": "RW", "level": "country", "name": "Rwanda"}])]
    for level, frame in inputs.units.items():
        metric = frame.to_crs(32735)
        part = pd.DataFrame(
            {
                "geo_id": frame.geo_id,
                "level": level,
                "name": frame.name,
                "parent_id": frame.parent_id,
                "nisr_code": frame.nisr_code,
                "area_km2": (metric.area / 1e6).round(2),
            }
        )
        if level == "province":
            part["province"] = part.name
        elif level == "district":
            part["province"] = part.parent_id.map(provinces)
            part["district"] = part.name
        else:
            part["district"] = part.parent_id.map(districts.name)
            part["province"] = part.parent_id.map(districts.parent_id).map(provinces)
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def sources(inputs: Inputs) -> pd.DataFrame:
    real = {
        "census_2022": inputs.census_sectors.real,
        "worldpop": inputs.under5 is not None,
        "projections": inputs.projections.real,
        "boundaries": inputs.boundaries_real,
        "osm": inputs.schools.real and inputs.schools.source == "osm",
        "schools": inputs.schools.source == schools_source.SOURCE,
        "yearbook": inputs.yearbook.real,
        "rdhs_2025": inputs.stunting.real,
        "eicv7": inputs.poverty.real,
        "ncda": inputs.supply.real,
    }
    rows = [
        {
            "source_id": d.key,
            "title": d.title,
            "publisher": d.publisher,
            "reference_period": d.reference_period,
            "url": d.url,
            "licence": d.licence,
            "loaded": real[d.key],
            "notes": None if real[d.key] else f"Missing: {d.fallback}",
        }
        for d in FILE_DATASETS
    ]
    rows.append(
        {
            "source_id": GEOBOUNDARIES,
            "title": "geoBoundaries gbOpen RWA (simplified)",
            "publisher": "geoBoundaries, William & Mary, from NISR open data",
            "reference_period": "2023",
            "url": "https://www.geoboundaries.org",
            "licence": "CC BY 4.0",
            "loaded": not inputs.boundaries_real,
            "notes": "Real shapes used while the official boundaries are missing",
        }
    )
    return pd.DataFrame(rows)


def estimate_2026(inputs: Inputs) -> pd.DataFrame:
    distance = far_shares(inputs.sectors, inputs.schools, inputs.raw, inputs.supply.frame)
    out = estimate(inputs).merge(distance, on="geo_id", how="left")
    # the layer inherits simulated status from simulated school points
    if not inputs.schools.real:
        out["distance_method"] = out.distance_method + ", simulated schools"
    elif inputs.schools.source == schools_source.SOURCE:
        # a partial list: far from a listed school is not proof of no school nearby
        out["distance_method"] = out.distance_method + (
            f", provisional: {len(inputs.schools.schools)} listed schools (standalone "
            "pre-primary only), an upper bound"
        )
    return out


def supply_extract(inputs: Inputs) -> pd.DataFrame:
    frame = inputs.supply.frame
    return frame.assign(status=inputs.supply.status)[
        ["centre_id", "name", "centre_type", "geo_id", "lon", "lat", "capacity", "enrolled_3_5",
         "caregivers", "as_of", "status"]
    ]  # fmt: skip


def write_geojson(inputs: Inputs, out: Path) -> None:
    for level in ("district", "sector"):
        frame = inputs.units[level][["geo_id", "name", "parent_id", "geometry"]]
        simple = frame.assign(geometry=frame.geometry.simplify(SIMPLIFY_DEGREES))
        (out / f"{level}s.geojson").write_text(json.dumps(json.loads(simple.to_json(drop_id=True))))
    write_schools(inputs.schools, out)


def write_schools(network: osm.Network, out: Path) -> None:
    """The school points the distance layer used, for the map, and the loader's report."""
    frame = network.schools
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r.lon), float(r.lat)]},
            "properties": {
                "name": str(getattr(r, "school_name", None) or r.school_id),
                "district": str(getattr(r, "district", None) or ""),
                "sector": str(getattr(r, "sector", None) or ""),
                "pupils": None
                if pd.isna(getattr(r, "preprimary_students_total", None))
                else int(r.preprimary_students_total),
                "status": network.status,
                "source": network.source,
            },
        }
        for r in frame.itertuples()
    ]
    (out / "schools.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    (out / "schools_report.json").write_text(
        json.dumps({"source": network.source, "status": network.status,
                    "points": len(features), **(network.report or {})})
    )  # fmt: skip


def build(
    raw: Path = RAW, eng: Engine | None = None, out: Path = PROCESSED
) -> dict[str, pd.DataFrame]:
    inputs = load_inputs(raw)
    tables: dict[str, pd.DataFrame] = {
        "geo_unit": geo_units(inputs),
        "source": sources(inputs),
        "observation": build_observations(inputs),
        "estimate_2026": estimate_2026(inputs),
    }
    tables.update(diagnose_step.run(inputs, tables))
    tables["forecast"] = forecast.forecast(inputs)
    tables["supply_extract"] = supply_extract(inputs)
    tables.update(content.load())
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        if name in PARQUET:
            frame.to_parquet(out / f"{name}.parquet", index=False)
    write_geojson(inputs, out)
    replace_analysis(eng or default_engine(), tables)
    return tables


def main() -> int:
    try:
        tables = build()
    except SchemaError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for name, frame in tables.items():
        print(f"{name:16} {len(frame):6} rows")
    missing = tables["source"].query("not loaded and source_id != @GEOBOUNDARIES").source_id
    # geoBoundaries shapes are real; only the NISR codes are missing while it stands in.
    simulated = [s for s in missing if s != "boundaries"]
    if "schools" not in set(missing):  # the MINEDUC list stands in for OSM: no simulated schools
        simulated = [s for s in simulated if s != "osm"]
    else:
        simulated = [s for s in simulated if s != "schools"]
    print(f"Simulated stand-ins used for: {', '.join(simulated) or 'nothing'}")
    report = json.loads((PROCESSED / "schools_report.json").read_text())
    if report["source"] == schools_source.SOURCE:
        print(
            f"Schools: PROVISIONAL list, {report['loaded']} of {report['features']} records "
            f"loaded; {report['invalid_coordinates']} invalid coordinates, "
            f"{report['missing_geometry']} without a point, {report['duplicate_points']} "
            f"repeated points; missing properties {report['missing_properties']}"
        )
    elif report.get("errors"):
        print(f"Schools: the school file was not used: {'; '.join(report['errors'])}")
    if "boundaries" in set(missing):
        coded = tables["geo_unit"].query("level == 'sector'").nisr_code.notna().sum()
        print(f"Boundaries: geoBoundaries shapes (real); {coded} of 416 sectors carry NISR codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
