"""Intake of the October 2026 deliveries: the NISR 2022 sector layer, the NCDA mapping extract,
the WorldPop layers, the school CSV export and the published tables that only verify what is
staged. The fixtures are made-up values in the received formats, not the real files."""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from irerero.config import DEMO, SIMULATED
from irerero.data import crosscheck, intake
from irerero.data.sources import boundaries, ncda, schools

CROSSWALK = pd.read_csv("data/reference/sector_name_crosswalk.csv", dtype=str)
CODES = CROSSWALK[CROSSWALK.source == "*"].set_index("geo_id")
DISTRICT_CODES = pd.read_csv("data/reference/district_name_crosswalk.csv", dtype=str)
DISTRICT_CODES = DISTRICT_CODES[DISTRICT_CODES.source == "*"].set_index("nisr_district_code")
PROVINCE_NAMES = {"1": "City of Kigali", "2": "Southern Province", "3": "Western Province",
                  "4": "Northern Province", "5": "Eastern Province"}  # fmt: skip


@pytest.fixture
def dirs(tmp_path: Path) -> dict[str, Path]:
    out = {k: tmp_path / k for k in ("in", "raw", "interim")}
    for p in out.values():
        p.mkdir()
    out["manifest"] = tmp_path / "received_files.csv"
    return out


def _run(dirs: dict[str, Path], files: list[Path]) -> list[intake.Result]:
    return intake.run(files, dirs["raw"], dirs["interim"], dirs["manifest"])


def _nisr_layer(path: Path) -> Path:
    """The demo sector shapes in the NISR 2022 layout: numeric ids, geometry before the
    attributes as in the published file."""
    shapes = gpd.read_file(DEMO / "boundaries" / "sectors.geojson")
    code = shapes.geo_id.map(CODES.nisr_sector_code).str[2:]
    district = code.str[:2]
    features = [
        {
            "type": "Feature",
            "geometry": json.loads(gpd.GeoSeries([g]).to_json())["features"][0]["geometry"],
            "properties": {
                "province": PROVINCE_NAMES[d[0]],
                "province_id": int(d[0]),
                "district": DISTRICT_CODES.source_district[f"RW{d}"],
                "district_id": int(d),
                "sector": n,
                "sector_id": int(c),
                "last_edited_date": 1725355226660,
            },
        }
        for g, c, d, n in zip(shapes.geometry, code, district, shapes.name, strict=True)
    ]
    target = path / "Rwanda_Sector_Boundaries_2022.geojson"
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return target


def test_nisr_sector_layer_becomes_the_three_boundary_files(dirs):
    path = _nisr_layer(dirs["in"])
    assert intake.classify([path])["nisr_boundaries"] == [path]  # found past the geometry
    (result,) = _run(dirs, [path])
    assert result.staged, [c.text for c in result.checks if c.level == "fail"]
    units, source, real = boundaries.load(dirs["raw"])
    assert real and source == boundaries.DATASET.key
    assert [len(units[level]) for level in boundaries.LEVELS] == [5, 30, 416]
    sectors = units["sector"]
    assert sectors.geo_id.notna().all() and sectors.parent_id.str.startswith("D-").all()
    assert set(units["district"].parent_id) == {p[0] for p in boundaries.PROVINCES.values()}
    # districts are the union of their sectors (the simplified demo shapes overlap a little;
    # the NISR layer tiles exactly)
    district_area = units["district"].to_crs(32735).area.sum()
    assert abs(district_area / sectors.to_crs(32735).area.sum() - 1) < 0.005


def test_nisr_layer_with_a_sector_in_two_districts_is_not_staged(dirs):
    path = _nisr_layer(dirs["in"])
    data = json.loads(path.read_text())
    data["features"][1]["properties"]["district_id"] = 11  # a Bugesera sector put in Nyarugenge
    path.write_text(json.dumps(data))
    (result,) = _run(dirs, [path])
    assert not result.staged
    assert any(c.level == "fail" for c in result.checks)


def _ncda(path: Path) -> Path:
    rows = [
        # ecd_code, name, setting, active, district, sector, 3-6, children, caregivers
        ("C1", "Centre A", "Home based ECD", "active", "Muhanga", "Cyeza", 12, 14, 1),
        ("C2", "Centre B", "School based ECD Centre", "active", "Muhanga", "Cyeza", 16611, 170, 3),
        (None, "Centre C", "Faith-based", "active", "Rulindo", "Shyorongi", 20, 22, 7777),
        ("C4", "Centre D", None, "active", "Muhanga", "Kibangu", 30, 25, 2),
        ("C5", "Closed", "Centre Based", "not_active", "Muhanga", "Cyeza", 10, 10, 1),
        ("C6", "Nowhere", "Centre Based", "active", None, None, 10, 10, 1),
    ]
    frame = pd.DataFrame(rows, columns=["ecd_code", "name_ecd_sercive", "settings_types",
                                        "active_not_active", "district_name", "sector_name",
                                        "total_three_to_six", "total_children",
                                        "total_caregivers"])  # fmt: skip
    frame["objectid"] = range(1, len(frame) + 1)
    frame["longitude"], frame["latitude"] = 29.75, -2.05
    frame["extract_date"] = "2026-10-30"
    frame["visited_date"] = 1755919140000
    frame.to_csv(path / "ncda_ecd_mapping_extract.csv", index=False)
    return path / "ncda_ecd_mapping_extract.csv"


def test_ncda_extract_keeps_active_services_and_invents_nothing(dirs):
    (result,) = _run(dirs, [_ncda(dirs["in"])])
    assert result.staged
    staged = pd.read_csv(dirs["raw"] / "ncda" / ncda.FILE)
    assert list(staged.centre_id) == ["C1", "C2", "NCDA-OBJ-3", "C4"]  # inactive, no place: out
    assert list(staged.centre_type) == ["home_based", "school_based", "other", "not_stated"]
    assert staged.capacity.isna().all() and staged.enrolled_3_5.isna().all()  # not in the extract
    assert staged.enrolled_3_6.tolist()[0] == 12 and pd.isna(staged.enrolled_3_6[1])  # 16,611
    assert pd.isna(staged.caregivers[2])  # 7,777 caregivers is an entry error, left empty
    assert staged.enrolled_3_6[3] == 30  # above its total by less than tenfold: kept as given
    text = " ".join(c.text for c in result.checks)
    assert "16,611" in text and "7,777" in text and "1 marked not active" in text


def test_ncda_extract_loads_beside_the_labelled_demo_centres_only_in_demo_mode(dirs):
    _run(dirs, [_ncda(dirs["in"])])
    with_demo = ncda.load(dirs["raw"], demo=True)
    alone = ncda.load(dirs["raw"], demo=False)
    assert with_demo.real and with_demo.status != SIMULATED
    assert set(alone.frame.status) == {ncda.DATASET.status}
    demo = with_demo.frame[with_demo.frame.status == SIMULATED]
    assert len(demo) and demo.centre_id.str.startswith("SIM-MUH-").all()
    assert len(with_demo.frame) == len(alone.frame) + len(demo)
    assert with_demo.frame.geo_id.notna().all()  # Shyorongi through the reviewed crosswalk


def _raster(path: Path, name: str) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    data = np.full((4, 4), 2.0, dtype="float32")
    target = path / name
    with rasterio.open(target, "w", driver="GTiff", height=4, width=4, count=1, dtype="float32",
                       crs="EPSG:4326", transform=from_origin(29.7, -2.0, 0.000833, 0.000833),
                       nodata=-99999.0) as dst:  # fmt: skip
        dst.write(data, 1)
    return target


def test_an_incomplete_worldpop_set_is_named_and_not_staged(dirs):
    files = [_raster(dirs["in"], f"rwa_{s}_{a}_2020_constrained_UNadj.tif")
             for s, a in (("f", "0"), ("f", "1"), ("m", "0"), ("f", "5"))]  # fmt: skip
    (result,) = _run(dirs, files)
    assert not result.staged and not (dirs["raw"] / "worldpop").exists()
    text = " ".join(c.text for c in result.checks)
    assert "missing rwa_m_1_2020_constrained_UNadj.tif" in text
    assert "f_5" in text  # ages 5 to 9: named, never summed into under-5


def test_complete_worldpop_set_is_reported_complete(tmp_path):
    files = [_raster(tmp_path, f"rwa_{s}_{a}_2026_CN_100m_R2025A_v1.tif")
             for s in "fm" for a in ("00", "01")]  # fmt: skip
    checks = crosscheck.worldpop_layers(files)
    assert any(c.level == "pass" and "complete" in c.text for c in checks)


def _schools(path: Path) -> tuple[Path, Path]:
    points = [(f"1101{i:02}", 30.0 + i / 100, -1.95, "Nyarugenge", "Gitega") for i in range(3)]
    features = [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [x, y]},
         "properties": {"school_code": c, "school_name": f"School {c}", "district": d,
                        "sector": s, "school_category": "PRE_PRIMARY",
                        "preprimary_students_total": 40}}
        for c, x, y, d, s in points
    ]  # fmt: skip
    geo = path / "rwanda_preprimary_schools.geojson"
    geo.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    csv = pd.DataFrame(
        [{"school_code": c, "school_category": "PRE_PRIMARY", "latitude": y, "longitude": x,
          "geometry_latitude": y, "geometry_longitude": x} for c, x, y, _, _ in points]
    )  # fmt: skip
    csv.to_csv(path / "rwanda_preprimary_schools.csv", index=False)
    return geo, path / "rwanda_preprimary_schools.csv"


def test_school_csv_and_geojson_are_one_list_staged_once(dirs):
    geo, csv = _schools(dirs["in"])
    copy = dirs["in"] / "Rwandapreprimarydata_locatios.GeoJSON"
    copy.write_text(geo.read_text())
    results = _run(dirs, [geo, copy, csv])
    staged = [r for r in results if r.staged]
    assert len(staged) == 1 and staged[0].staged.name == schools.FILE
    text = " ".join(c.text for r in results for c in r.checks)
    assert "holds the same 3 records" in text
    assert "3 share a code with the GeoJSON, 0 only in the CSV, 0 only in the GeoJSON" in text
    assert all(c.level != "fail" for r in results for c in r.checks)


def test_school_csv_with_a_record_the_geojson_lacks_fails(dirs):
    geo, csv = _schools(dirs["in"])
    frame = pd.read_csv(csv, dtype=str)
    frame.loc[len(frame)] = ["999999", "PRE_PRIMARY", "-1.9", "30.1", "-1.9", "30.1"]
    frame.to_csv(csv, index=False)
    checks = crosscheck.school_csv(csv, geo)
    assert checks[0].level == "fail" and "1 only in the CSV" in checks[0].text


def test_the_distance_layer_never_counts_mapped_or_simulated_centres_as_schools(monkeypatch):
    from irerero.config import NCDA_IN_DISTANCE
    from irerero.pipeline import build

    assert NCDA_IN_DISTANCE is False
    seen = {}

    def fake(sectors, network, raw, extra=None):
        seen["extra"] = extra
        return pd.DataFrame({"geo_id": sectors.geo_id, "far_share": 0.5,
                             "distance_method": "straight", "children_spread": "even"})  # fmt: skip

    monkeypatch.setattr(build, "far_shares", fake)
    monkeypatch.setattr(build, "estimate", lambda inputs: inputs.sectors[["geo_id"]].copy())
    from irerero.pipeline.inputs import load_inputs

    build.estimate_2026(load_inputs(Path(DEMO).parent / "no-raw-here"))
    assert seen["extra"] is None


def test_learn_simulation_runs_only_in_demo_mode(monkeypatch, tmp_path):
    from sqlalchemy import create_engine

    from irerero.db.models import Base
    from irerero.learn import simulate

    eng = create_engine(f"sqlite:///{tmp_path / 'app.sqlite'}")
    Base.metadata.create_all(eng)
    monkeypatch.setenv("DEMO_MODE", "false")
    assert simulate.seed(eng) is False


def _dhs_pr(path: Path) -> Path:
    """A made-up household-member recode: 30 districts, 2 strata each, 4 clusters per stratum,
    children whose height-for-age puts a known share below -2 SD."""
    rng = np.random.default_rng(1)
    rows = []
    codes = DISTRICT_CODES.index.str[2:].astype(int)
    for d in codes:
        for stratum in (1, 2):
            for cluster in range(4):
                for child in range(10):
                    rows.append({
                        "hv000": "RW8", "hv005": 1_000_000, "hv007": 2025,
                        "hv021": d * 100 + stratum * 10 + cluster, "hv022": d * 10 + stratum,
                        "hv103": 1, "hc70": float(-250 if child < 3 else rng.integers(-150, 100)),
                        "shdistrict": d,
                    })  # fmt: skip
    frame = pd.DataFrame(rows)
    frame.loc[0, "hc70"] = 9998  # flagged: left out
    frame.loc[1, "hv103"] = 0  # not de facto: left out
    target = path / "RWPR91FL.dta"
    frame.to_stata(target, write_index=False)
    return target


def test_dhs_microdata_becomes_district_stunting_with_intervals(dirs):
    import zipfile

    from irerero.config import MODEL
    from irerero.data.sources import rdhs

    pr = _dhs_pr(dirs["in"])
    archive = dirs["in"] / "Microdata (1).zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(pr, "Microdata/Microdata/RWPR91FL.dta")
        zf.writestr("Microdata/Microdata/RWIR91FL.dta", b"not needed")
    files = intake._expand([str(archive)], dirs["interim"])
    assert [f.name for f in files] == ["RWPR91FL.dta"]  # only the recode intake reads
    (result,) = _run(dirs, files)
    assert result.staged, [c.text for c in result.checks if c.level == "fail"]
    loaded = rdhs.load(dirs["raw"])
    frame = loaded.frame
    assert loaded.status == MODEL and len(frame) == 30 and frame.geo_id.notna().all()
    assert set(frame.columns) >= {"stunting_u5", "stunting_u5_low", "stunting_u5_high"}
    assert (
        (frame.stunting_u5_low <= frame.stunting_u5) & (frame.stunting_u5 <= frame.stunting_u5_high)
    ).all()
    assert abs(frame.stunting_u5.median() - 0.3) < 0.02  # 3 of every 10 children
    assert "1 flagged" in " ".join(c.text for c in result.checks)


def test_eicv_microdata_checks_the_published_rates_and_stages_nothing(dirs):
    from irerero.data import crosscheck

    names = DISTRICT_CODES.source_district
    rates = {name: 0.1 + i / 100 for i, name in enumerate(names)}
    (dirs["raw"] / "eicv7").mkdir()
    pd.DataFrame(
        {
            "level": "district",
            "district_name": list(rates),
            "sector_name": "",
            "poverty_rate": list(rates.values()),
        }
    ).to_csv(dirs["raw"] / "eicv7" / "eicv7_poverty.csv", index=False)
    rows = []
    for code, name in names.items():
        poor = round(rates[name] * 100)
        district = int(code[2:])
        rows += [
            {"district": district, "clust": district * 10 + i % 3,
             "pov_jan": 100.0 if i < poor else 0.0, "pop_wt": 1.0}
            for i in range(100)
        ]  # fmt: skip
    path = dirs["in"] / "CS_EICV7_poverty_file.dta"
    pd.DataFrame(rows).to_stata(path, write_index=False)
    checks = crosscheck.eicv_microdata(path, dirs["raw"])
    assert any("30 of 30 districts" in c.text for c in checks)


def _osm(path: Path) -> Path:
    """A made-up extract: one school point, a footpath to it, a road, and a building the
    intake must leave out."""
    import osmium

    target = path / "rwanda-261029.osm.pbf"
    lon0, lat0, m = 29.74, -2.07, 1 / 111_320
    with osmium.SimpleWriter(str(target)) as out:
        school = {"amenity": "school", "name": "Test school"}
        out.add_node(osmium.osm.mutable.Node(id=1, location=(lon0, lat0), tags=school))
        for i in range(2, 6):
            out.add_node(osmium.osm.mutable.Node(id=i, location=(lon0 + (i - 2) * 300 * m, lat0)))
        out.add_node(osmium.osm.mutable.Node(id=9, location=(lon0, lat0 + 0.01)))
        out.add_node(osmium.osm.mutable.Node(id=10, location=(lon0 + 0.001, lat0 + 0.01)))
        out.add_way(osmium.osm.mutable.Way(id=100, nodes=[2, 3, 4, 5], tags={"highway": "footway"}))
        out.add_way(osmium.osm.mutable.Way(id=200, nodes=[9, 10], tags={"building": "yes"}))
    return target


def test_osm_extract_keeps_schools_and_walkable_roads_only(dirs):
    from irerero.data.sources import osm

    (result,) = _run(dirs, [_osm(dirs["in"])])
    assert result.staged and result.staged.name == osm.PBF
    network = osm.load(dirs["raw"])
    assert len(network.schools) == 1 and network.has_roads
    ids, *_ = network.road_arrays()
    assert set(ids.tolist()) == {2, 3, 4, 5}  # the building's nodes are not kept
    assert "1 schools and 0 kindergartens" in " ".join(c.text for c in result.checks)


def test_osm_and_mineduc_schools_are_combined_and_counted_once(dirs):
    from irerero.config import PROVISIONAL
    from irerero.pipeline.inputs import COMBINED, school_network

    _run(dirs, [_osm(dirs["in"])])
    m = 1 / 111_320
    features = [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [29.74 + 40 * m, -2.07]},
         "properties": {"school_code": "1", "school_category": "PRE_PRIMARY"}},  # same site
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [29.80, -2.10]},
         "properties": {"school_code": "2", "school_category": "PRE_PRIMARY"}},
    ]  # fmt: skip
    (dirs["raw"] / "schools").mkdir()
    (dirs["raw"] / "schools" / "schools.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    network = school_network(dirs["raw"])
    assert network.source == COMBINED and network.status == PROVISIONAL
    assert len(network.schools) == 2  # the OSM school and the MINEDUC school elsewhere
    assert network.report["mineduc_same_site"] == 1 and network.report["osm_points"] == 1
    assert sorted(network.schools.origin) == ["mineduc", "openstreetmap"]
