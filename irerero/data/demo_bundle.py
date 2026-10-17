"""Generate the committed demo bundle in data/demo/ and the crosswalks in data/reference/.

    python -m irerero.data.demo_bundle

Run once (already run; the output is in git). It needs the geoBoundaries files in
data/raw/geoboundaries/ (CC BY 4.0). Every number it writes is SIMULATED with seed 2026, in
the same file format as the real dataset, so one loader reads both. The shapes are real public
boundaries, simplified to stay small.
"""

import json
import math
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from irerero.config import DEMO, RAW, REFERENCE, SEED

GB = RAW / "geoboundaries"
KIGALI = {"Gasabo", "Kicukiro", "Nyarugenge"}
LEARN_PILOT = "Muhanga"
# Simplify to about 150 m and round to 5 decimals: enough for sector maps, small in git.
SIMPLIFY_DEGREES = 0.0014
EXPECTED = {"province": 5, "district": 30, "sector": 416}


def slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().upper()
    return "-".join(p for p in re.split(r"[^A-Z0-9]+", plain) if p)


def _boundaries() -> dict[str, gpd.GeoDataFrame]:
    adm = {
        level: gpd.read_file(GB / f"geoBoundaries-RWA-{code}_simplified.geojson")
        for level, code in (("province", "ADM1"), ("district", "ADM2"), ("sector", "ADM3"))
    }
    provinces = adm["province"].assign(
        geo_id=lambda f: "P-" + f.shapeName.str.removesuffix(" Province").map(slug),
        parent_id="RW",
    )
    districts = adm["district"].copy()
    districts["parent_id"] = _parent(districts, provinces)
    districts["geo_id"] = "D-" + districts.shapeName.map(slug)
    sectors = adm["sector"].copy()
    sectors["parent_id"] = _parent(sectors, districts)
    sectors["geo_id"] = (
        "S-" + sectors.parent_id.str.removeprefix("D-") + "-" + sectors.shapeName.map(slug)
    )
    out = {}
    for level, frame in (("province", provinces), ("district", districts), ("sector", sectors)):
        frame = frame.rename(columns={"shapeName": "name"})[
            ["geo_id", "name", "parent_id", "geometry"]
        ]
        if frame.parent_id.isna().any() or frame.geo_id.duplicated().any():
            raise RuntimeError(f"{level}: missing parents or duplicate codes")
        if len(frame) != EXPECTED[level]:
            raise RuntimeError(f"{level}: {len(frame)} units, expected {EXPECTED[level]}")
        out[level] = frame.sort_values("geo_id").reset_index(drop=True)
    return out


def _parent(children: gpd.GeoDataFrame, parents: gpd.GeoDataFrame) -> pd.Series:
    """The parent containing each child's interior point."""
    points = children.assign(geometry=children.representative_point())
    joined = gpd.sjoin(points, parents[["geo_id", "geometry"]], predicate="within", how="left")
    return joined.groupby(level=0).geo_id.first()


def _write_geojson(frame: gpd.GeoDataFrame, path: Path) -> None:
    simple = frame.assign(
        geometry=frame.geometry.simplify(SIMPLIFY_DEGREES, preserve_topology=True)
    )
    data = json.loads(simple.to_json(drop_id=True))
    for feature in data["features"]:
        feature["geometry"] = _rounded(feature["geometry"])
    path.write_text(json.dumps(data, separators=(",", ":")))


def _rounded(geometry: dict) -> dict:
    def walk(coords):  # type: ignore[no-untyped-def]
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 5), round(coords[1], 5)]
        return [walk(c) for c in coords]

    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}


def _crosswalks(units: dict[str, gpd.GeoDataFrame]) -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    districts = units["district"].set_index("geo_id").name
    sectors = units["sector"]
    pd.DataFrame(
        {
            "geo_id": sectors.geo_id,
            "nisr_sector_code": "",
            "source": "*",
            "source_district": sectors.parent_id.map(districts),
            "source_sector": sectors.name,
            "reviewed": "no",
            "note": "geoBoundaries spelling; add the NISR code and source spellings when reviewed",
        }
    ).to_csv(REFERENCE / "sector_name_crosswalk.csv", index=False)
    pd.DataFrame(
        {
            "geo_id": districts.index,
            "nisr_district_code": "",
            "source": "*",
            "source_district": districts.values,
            "reviewed": "no",
        }
    ).to_csv(REFERENCE / "district_name_crosswalk.csv", index=False)


def _sector_frame(units: dict[str, gpd.GeoDataFrame], rng: np.random.Generator) -> pd.DataFrame:
    sectors = units["sector"].copy()
    districts = units["district"].set_index("geo_id").name
    metric = sectors.to_crs(32735)
    sectors["area_km2"] = metric.area / 1e6
    sectors["district_name"] = sectors.parent_id.map(districts)
    sectors["kigali"] = sectors.district_name.isin(KIGALI)
    # The two smallest sectors of each district are its towns.
    sectors["town"] = sectors.groupby("parent_id").area_km2.rank(method="first") <= 2
    urban = np.where(
        sectors.kigali,
        rng.uniform(0.6, 1.0, len(sectors)),
        np.where(
            sectors.town,
            rng.uniform(0.35, 0.85, len(sectors)),
            rng.uniform(0.0, 0.12, len(sectors)),
        ),
    )
    sectors["urban_share"] = urban.round(3)
    density = np.where(sectors.kigali, 2600, 420) * rng.lognormal(0, 0.35, len(sectors))
    density = np.where(sectors.town & ~sectors.kigali, density * 2.2, density)
    sectors["population"] = np.clip(density * sectors.area_km2, 9000, 95000).round()
    return sectors


def _census(sectors: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    n = len(sectors)
    u = sectors.urban_share.to_numpy()
    pop = sectors.population.to_numpy()
    water = np.clip(0.62 + 0.3 * u + rng.normal(0, 0.06, n), 0.3, 0.99)
    sanitation = np.clip(0.55 + 0.3 * u + rng.normal(0, 0.08, n), 0.2, 0.98)
    electricity = np.clip(0.3 + 0.6 * u + rng.normal(0, 0.1, n), 0.05, 0.99)
    women_secondary = np.clip(0.14 + 0.38 * u + rng.normal(0, 0.05, n), 0.04, 0.8)
    poverty = np.clip(0.42 - 0.3 * u + rng.normal(0, 0.06, n), 0.04, 0.7)
    district_effect = sectors.parent_id.map(
        {d: rng.normal(0, 0.25) for d in sectors.parent_id.unique()}
    ).to_numpy()
    logit = (
        -1.55
        + 1.35 * u
        + 1.6 * (women_secondary - 0.25)
        + 0.9 * (water - 0.75)
        - 1.4 * (poverty - 0.3)
        + district_effect
        + rng.normal(0, 0.22, n)
    )
    rate = 1 / (1 + np.exp(-logit))
    children_0_4 = np.round(pop * rng.uniform(0.125, 0.145, n))
    children_3_5 = np.round(children_0_4 * rng.uniform(0.58, 0.64, n))
    attending = np.round(children_3_5 * rate)
    households = np.round(pop / rng.uniform(4.0, 4.6, n))
    frame = pd.DataFrame(
        {
            "district_name": sectors.district_name,
            "sector_name": sectors.name,
            "population": pop.astype(int),
            "children_0_4": children_0_4.astype(int),
            "children_3_5": children_3_5.astype(int),
            "children_3_5_attending": attending.astype(int),
            "children_3_5_never_attended": (children_3_5 - attending).astype(int),
            "urban_share": sectors.urban_share,
            "households": households.astype(int),
            "hh_improved_water": np.round(households * water).astype(int),
            "hh_improved_sanitation": np.round(households * sanitation).astype(int),
            "hh_electricity": np.round(households * electricity).astype(int),
            "women_secondary_share": women_secondary.round(3),
            "source_page": "simulated",
        }
    )
    return frame, poverty


def _district_totals(census: pd.DataFrame) -> pd.DataFrame:
    counts = [
        "population",
        "children_0_4",
        "children_3_5",
        "children_3_5_attending",
        "children_3_5_never_attended",
        "households",
        "hh_improved_water",
        "hh_improved_sanitation",
        "hh_electricity",
    ]
    totals = census.groupby("district_name")[counts].sum().reset_index()
    totals["source_page"] = "simulated"
    return totals


def _projections(totals: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for row in totals.itertuples():
        growth = rng.uniform(0.018, 0.029)
        for year in range(2023, 2033):
            population = row.population * (1 + growth) ** (year - 2022)
            rows.append(
                {
                    "district_name": row.district_name,
                    "year": year,
                    "population": round(population),
                    "population_low": round(population * (1 - 0.01 * (year - 2022) ** 0.5)),
                    "population_high": round(population * (1 + 0.01 * (year - 2022) ** 0.5)),
                    "source_page": "simulated",
                }
            )
    return pd.DataFrame(rows)


def _yearbook(
    census: pd.DataFrame, projections: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    share_3_5 = census.groupby("district_name").apply(
        lambda d: d.children_3_5.sum() / d.population.sum(), include_groups=False
    )
    base = census.groupby("district_name").apply(
        lambda d: d.children_3_5_attending.sum() / d.children_3_5.sum(), include_groups=False
    )
    population = projections.set_index(["district_name", "year"]).population
    rows = []
    for district in census.district_name.unique():
        slope = rng.uniform(0.012, 0.038)
        start = base[district] * rng.uniform(0.9, 1.25) - 2 * slope
        for i, school_year in enumerate(("2020/21", "2021/22", "2022/23", "2023/24", "2024/25")):
            first_year = 2020 + i
            pop = population.get((district, max(first_year, 2023)), np.nan)
            if first_year < 2023:
                pop = population[(district, 2023)] / (1.023 ** (2023 - first_year))
            rate = max(0.05, start + slope * i + rng.normal(0, 0.008))
            pupils = rate * pop * share_3_5[district]
            classrooms = pupils / rng.uniform(38, 70)
            teachers = pupils / rng.uniform(24, 46)
            rows.append(
                {
                    "district_name": district,
                    "school_year": school_year,
                    "pupils": round(pupils),
                    "schools": round(classrooms / rng.uniform(1.6, 2.6)),
                    "classrooms": round(classrooms),
                    "teachers": round(teachers),
                    "qualified_teachers": round(teachers * rng.uniform(0.45, 0.92)),
                    "source_page": "simulated",
                }
            )
    return pd.DataFrame(rows)


def _stunting(districts: pd.Series, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for name in districts:
        value = rng.uniform(0.12, 0.25) if name in KIGALI else rng.uniform(0.2, 0.43)
        if name == "Gicumbi":
            value = 0.388  # the published RDHS 2025 figure quoted in the brief
        half = rng.uniform(0.03, 0.06)
        rows.append(
            {
                "district_name": name,
                "stunting_u5": round(value, 3),
                "stunting_u5_low": round(max(0.0, value - half), 3),
                "stunting_u5_high": round(min(1.0, value + half), 3),
                "source_page": "simulated",
            }
        )
    return pd.DataFrame(rows)


def _schools(sectors: gpd.GeoDataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for row in sectors.itertuples():
        count = max(1, rng.poisson(row.area_km2 / 5 + 4 * row.urban_share + 1))
        minx, miny, maxx, maxy = row.geometry.bounds
        placed = 0
        while placed < count:
            point = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if row.geometry.contains(point):
                placed += 1
                rows.append(
                    {
                        "school_id": f"SIM-{row.geo_id.removeprefix('S-')}-{placed}",
                        "lon": round(point.x, 5),
                        "lat": round(point.y, 5),
                    }
                )
    return pd.DataFrame(rows)


def _supply(sectors: gpd.GeoDataFrame, rng: np.random.Generator) -> pd.DataFrame:
    pilot = sectors[sectors.district_name == LEARN_PILOT]
    types = ["home_based", "community_based", "school_based", "centre_based"]
    capacity = {
        "home_based": (15, 30),
        "community_based": (35, 70),
        "school_based": (40, 90),
        "centre_based": (50, 110),
    }
    rows, n = [], 0
    for row in pilot.itertuples():
        minx, miny, maxx, maxy = row.geometry.bounds
        for _ in range(rng.integers(2, 5)):
            while True:
                point = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
                if row.geometry.contains(point):
                    break
            n += 1
            kind = types[rng.choice(4, p=[0.4, 0.3, 0.2, 0.1])]
            cap = int(rng.integers(*capacity[kind]))
            rows.append(
                {
                    "centre_id": f"SIM-MUH-{n:03d}",
                    "name": f"Simulated centre {n} ({row.name})",
                    "centre_type": kind,
                    "district_name": LEARN_PILOT,
                    "sector_name": row.name,
                    "lon": round(point.x, 5),
                    "lat": round(point.y, 5),
                    "capacity": cap,
                    "enrolled_3_5": int(cap * rng.uniform(0.6, 1.15)),
                    "caregivers": max(1, round(cap / rng.uniform(15, 32))),
                    "as_of": "2026-09-30",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    units = _boundaries()
    folder = DEMO / "boundaries"
    folder.mkdir(parents=True, exist_ok=True)
    for level, frame in units.items():
        _write_geojson(frame, folder / f"{level}s.geojson")
    _crosswalks(units)

    sectors = _sector_frame(units, rng)
    census, poverty = _census(sectors, rng)
    totals = _district_totals(census)
    projections = _projections(totals, rng)
    files = {
        "census_2022/census_2022_sectors.csv": census,
        "census_2022/census_2022_districts.csv": totals,
        "projections/nisr_projections_2023_2032.csv": projections,
        "yearbook/mineduc_yearbook_preprimary.csv": _yearbook(census, projections, rng),
        "rdhs_2025/rdhs_2025_stunting.csv": _stunting(totals.district_name, rng),
        "eicv7/eicv7_poverty.csv": pd.DataFrame(
            {
                "level": "sector",
                "district_name": census.district_name,
                "sector_name": census.sector_name,
                "poverty_rate": poverty.round(3),
                "source_page": "simulated",
            }
        ),
        "osm/schools.csv": _schools(sectors, rng),
        "ncda/supply_extract.csv": _supply(sectors, rng),
    }
    for name, frame in files.items():
        path = DEMO / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    print(f"Wrote {len(files)} simulated tables and 3 boundary files to {DEMO}")
    print(
        f"Children 3-5 (simulated): {census.children_3_5.sum():,}; "
        f"attending {census.children_3_5_attending.sum() / census.children_3_5.sum():.1%}"
    )
    smallest, largest = math.floor(sectors.area_km2.min()), math.ceil(sectors.area_km2.max())
    print(f"Sector area range: {smallest}-{largest} km2")


if __name__ == "__main__":
    main()
