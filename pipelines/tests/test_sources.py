"""Every loader against small synthetic files. Nothing here is real data.

Each test loads inside a transaction that is rolled back, so the shared demo database is
unchanged afterwards.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, insert, text

from irerero_contract.tables import PipelineRun
from pipelines.need_model import apply_loaded_need
from pipelines.sources.base import Loader
from pipelines.sources.boundaries import _official_units
from pipelines.sources.census_2022 import Census2022
from pipelines.sources.covariates import Srtm
from pipelines.sources.ecd_centres import EcdCentres
from pipelines.sources.facilities import HealthFacilities
from pipelines.sources.lfs_2025 import Lfs2025
from pipelines.sources.osm import Osm, pilot_bbox, read_extract, road_network
from pipelines.sources.rdhs_2025 import Rdhs2025
from pipelines.sources.readers import SchemaError
from pipelines.sources.worldpop import FILES as WORLDPOP_FILES
from pipelines.sources.worldpop import WorldPop

# A box over Byumba, Gicumbi's town sector, in EPSG:4326.
WEST, NORTH, EAST, SOUTH = 30.03, -1.55, 30.09, -1.62


@pytest.fixture
def conn(demo_engine: Engine) -> Iterator[Connection]:
    with demo_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def _run_id(conn: Connection, pipeline: str) -> uuid.UUID:
    run_id = uuid.uuid4()
    conn.execute(
        insert(PipelineRun).values(
            id=run_id,
            pipeline=pipeline,
            origin="official",
            status="running",
            started_at=datetime.now(UTC),
            code_version="test",
            inputs=[],
            row_counts={},
            checks=[],
        )
    )
    return run_id


def _load(conn: Connection, loader: Loader, folder: Path) -> dict[str, int]:
    return loader.load(conn, folder, _run_id(conn, loader.dataset.key)).rows


def _write(folder: Path, name: str, content: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(content)
    return folder


def test_census_by_sector_name_replaces_simulated_children(
    conn: Connection, tmp_path: Path
) -> None:
    folder = _write(
        tmp_path,
        "census_2022_areas.csv",
        "admin_level,admin_code,admin_name,children_0_2,children_3_6,households,"
        "households_improved_water\n"
        "sector,,Byumba,4000,5000,9000,7200\n"
        "sector,,Cyumba,1500,2100,,\n",
    )
    assert _load(conn, Census2022(), folder) == {"area_indicator": 5}
    assert apply_loaded_need(conn) == 2
    row = conn.execute(
        text("SELECT * FROM need_estimate WHERE area_code = 'S-GICUMBI-BYUMBA'")
    ).one()
    assert (row.children_0_2_estimate, row.children_0_2_low, row.children_0_2_high) == (
        4000,
        3800,
        4200,
    )
    assert row.source.startswith("children: Fifth Rwanda Population and Housing Census")
    # Stunting and the barrier are still simulated, so the row stays labelled simulated.
    assert row.origin == "simulated"
    water = conn.execute(
        text(
            "SELECT value FROM area_indicator WHERE area_code = 'S-GICUMBI-BYUMBA' "
            "AND indicator = 'households_improved_water_share'"
        )
    ).scalar_one()
    assert water == pytest.approx(0.8)


def test_a_sector_takes_its_district_survey_value_with_a_wider_interval(
    conn: Connection, tmp_path: Path
) -> None:
    rdhs = _write(
        tmp_path / "rdhs",
        "rdhs_2025_key_indicators.csv",
        "admin_level,admin_name,stunting_u5,stunting_u5_low,stunting_u5_high\n"
        "district,Gicumbi,0.388,0.35,0.43\n",
    )
    lfs = _write(
        tmp_path / "lfs",
        "lfs_2025_districts.csv",
        "admin_level,admin_name,women_lfp_rate_mothers_u3,mothers_childcare_barrier_share\n"
        "district,Gicumbi,0.52,0.31\n",
    )
    census = _write(
        tmp_path / "census",
        "census_2022_areas.csv",
        "admin_level,admin_name,parent_name,children_0_2,children_3_6\n"
        "sector,Rukomo,Gicumbi,2000,2600\n",
    )
    _load(conn, Rdhs2025(), rdhs)
    _load(conn, Lfs2025(), lfs)
    _load(conn, Census2022(), census)
    apply_loaded_need(conn)
    sector = conn.execute(
        text("SELECT * FROM need_estimate WHERE area_code = 'S-GICUMBI-RUKOMO'")
    ).one()
    assert sector.stunting_risk_estimate == pytest.approx(0.388)
    assert sector.stunting_risk_low == pytest.approx(0.388 - 0.04 * 1.5)
    assert sector.stunting_risk_high == pytest.approx(0.388 + 0.04 * 1.5)
    # No interval published: the sector still gets the minimum width.
    assert sector.mothers_barrier_share_high - sector.mothers_barrier_share_low == pytest.approx(
        0.1
    )
    assert sector.origin == "official"
    district = conn.execute(text("SELECT * FROM need_estimate WHERE area_code = 'D-GICUMBI'")).one()
    assert (district.stunting_risk_low, district.stunting_risk_high) == (0.35, 0.43)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("admin_level,admin_name,children_0_2\nsector,Byumba,1\n", "missing column"),
        ("admin_level,admin_name,children_0_2,children_3_6\nsector,Atlantis,1,2\n", "Atlantis"),
        ("admin_level,admin_name,children_0_2,children_3_6\nsector,Byumba,-1,2\n", "negative"),
        ("admin_level,admin_name,children_0_2,children_3_6\nsector,,1,2\n", "admin_code"),
        (
            "admin_level,admin_name,children_0_2,children_3_6\n"
            "sector,Byumba,1,2\nsector,BYUMBA,3,4\n",
            "more than one row",
        ),
        ("admin_level,admin_name,children_0_2,children_3_6\nhamlet,Byumba,1,2\n", "admin_level"),
        (
            "admin_level,admin_name,children_0_2,children_3_6\nsector,Rukomo,1,2\n",
            "give parent_name",
        ),
    ],
)
def test_bad_area_files_stop_with_a_clear_message(
    conn: Connection, tmp_path: Path, content: str, message: str
) -> None:
    folder = _write(tmp_path, "census_2022_areas.csv", content)
    with pytest.raises(SchemaError, match=message):
        _load(conn, Census2022(), folder)


def test_intervals_must_be_complete_and_ordered(conn: Connection, tmp_path: Path) -> None:
    folder = _write(
        tmp_path,
        "rdhs_2025_key_indicators.csv",
        "admin_level,admin_name,stunting_u5,stunting_u5_low,stunting_u5_high\n"
        "district,Gicumbi,0.388,0.40,0.43\n",
    )
    with pytest.raises(SchemaError, match="_low <="):
        _load(conn, Rdhs2025(), folder)
    shares = _write(
        tmp_path / "shares",
        "rdhs_2025_key_indicators.csv",
        "admin_level,admin_name,stunting_u5\ndistrict,Gicumbi,38.8\n",
    )
    with pytest.raises(SchemaError, match="share between 0 and 1"):
        _load(conn, Rdhs2025(), shares)


def test_ncda_centres_load_with_their_sector(conn: Connection, tmp_path: Path) -> None:
    folder = _write(
        tmp_path,
        "ecd_centres.csv",
        "centre_id,name,centre_type,lon,lat,capacity,enrolment,enrolment_as_of,serves_0_2,"
        "serves_3_6,offers_meals,water_available\n"
        "A1,Test centre one,Home-based,30.065,-1.58,20,26,2026-09-01,yes,yes,no,yes\n"
        "A2,Test centre two,community_based,30.07,-1.59,50,40,2026-09-01,yes,yes,yes,no\n",
    )
    assert _load(conn, EcdCentres(), folder) == {"centre": 2}
    centre = conn.execute(text("SELECT * FROM centre WHERE code = 'NCDA-A1'")).one()
    assert (centre.type, centre.sector_code, centre.origin) == (
        "home_based",
        "S-GICUMBI-BYUMBA",
        "partner",
    )
    assert centre.fee_band is None and centre.ncda_ref == "A1"


def test_ncda_centres_reject_implausible_enrolment(conn: Connection, tmp_path: Path) -> None:
    folder = _write(
        tmp_path,
        "ecd_centres.csv",
        "centre_id,name,centre_type,lon,lat,capacity,enrolment,enrolment_as_of,serves_0_2,"
        "serves_3_6,offers_meals,water_available\n"
        "A1,Typo centre,home_based,30.065,-1.58,20,400,2026-09-01,yes,yes,no,yes\n",
    )
    with pytest.raises(SchemaError, match="three times capacity"):
        _load(conn, EcdCentres(), folder)


def test_health_facilities_must_be_in_rwanda(conn: Connection, tmp_path: Path) -> None:
    good = _write(
        tmp_path / "good",
        "health_facilities.csv",
        "facility_id,name,facility_type,lon,lat\n1,Byumba hospital,hospital,30.067,-1.578\n",
    )
    assert _load(conn, HealthFacilities(), good) == {"facility": 1}
    swapped = _write(
        tmp_path / "swapped",
        "health_facilities.csv",
        "facility_id,name,facility_type,lon,lat\n2,Swapped,clinic,-1.578,30.067\n",
    )
    with pytest.raises(SchemaError, match="outside Rwanda"):
        _load(conn, HealthFacilities(), swapped)


def _raster(path: Path, value: float, size: float = 0.001) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    width, height = round((EAST - WEST) / size), round((NORTH - SOUTH) / size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(WEST, NORTH, size, size),
        nodata=-99999,
    ) as out:
        rows = np.arange(height, dtype="float32")[:, None]
        out.write((value + rows * 0.1 + np.zeros((height, width), "float32"))[None, :, :])


def test_worldpop_places_children_in_500_m_cells(conn: Connection, tmp_path: Path) -> None:
    # The demo build spread children evenly; WorldPop replaces that spread.
    conn.execute(text("DELETE FROM population_cell"))
    for name, _ in WORLDPOP_FILES:
        _raster(tmp_path / name, 0.05)
    rows = _load(conn, WorldPop(), tmp_path)
    assert rows["population_cell"] > 0
    shares = dict(
        conn.execute(
            text(
                "SELECT sector_code, sum(share) FROM population_cell WHERE source LIKE 'WorldPop%' "
                "GROUP BY sector_code"
            )
        ).all()
    )
    assert "S-GICUMBI-BYUMBA" in shares
    assert all(total == pytest.approx(1.0) for total in shares.values())


def test_srtm_gives_sector_elevation_and_slope(conn: Connection, tmp_path: Path) -> None:
    _raster(tmp_path / "srtm_elevation_m.tif", 2000.0)
    _load(conn, Srtm(), tmp_path)
    values = dict(
        conn.execute(
            text(
                "SELECT indicator, value FROM area_indicator "
                "WHERE area_code = 'S-GICUMBI-BYUMBA' AND origin = 'public'"
            )
        ).all()
    )
    assert 2000 < values["elevation_m_mean"] < 2010
    # 0.1 m more per 0.001 degree row (about 111 m): a slope of about 0.05 degrees.
    assert values["slope_deg_mean"] == pytest.approx(0.0516, abs=0.005)


def test_osm_ways_become_a_walking_network(conn: Connection, tmp_path: Path) -> None:
    import osmium
    from osmium.osm.mutable import Node, Way

    path = tmp_path / "rwanda-latest.osm.pbf"
    with osmium.SimpleWriter(str(path)) as writer:
        for i, (lon, lat) in enumerate([(30.06, -1.58), (30.07, -1.58), (30.08, -1.58)], 1):
            writer.add_node(Node(id=i, location=(lon, lat), tags={}))
        writer.add_node(
            Node(id=9, location=(30.065, -1.585), tags={"amenity": "school", "name": "EP Test"})
        )
        writer.add_way(Way(id=1, nodes=[1, 2, 3], tags={"highway": "path"}))
        writer.add_way(Way(id=2, nodes=[1, 3], tags={"highway": "service", "access": "private"}))
    assert _load(conn, Osm(), tmp_path) == {"facility": 1}
    extract = read_extract(path, pilot_bbox(conn, ["D-GICUMBI"]))
    assert extract.edges == [(1, 2), (2, 3)]
    network = road_network(conn, extract, 67.0)
    start, end = network.nodes[1], network.nodes[3]
    [minutes] = network.minutes(start, [end], 60)
    assert minutes == pytest.approx(start.distance_to(end) / 67.0, rel=0.01)


def test_official_boundaries_keep_internal_codes_and_add_nisr_codes() -> None:
    staged = [
        {"adm": "ADM1", "name": "Northern Province", "shape_id": "4", "parent_id": None},
        {"adm": "ADM2", "name": "Gicumbi", "shape_id": "41", "parent_id": "4"},
        {"adm": "ADM3", "name": "Byumba", "shape_id": "4105", "parent_id": "41"},
        {"adm": "ADM4", "name": "Gisuna", "shape_id": "410502", "parent_id": "4105"},
    ]
    units = {u["nisr"]: u for u in _official_units(staged)}
    assert units["41"]["code"] == "D-GICUMBI"
    assert units["4105"] == units["4105"] | {"code": "S-GICUMBI-BYUMBA", "parent": "D-GICUMBI"}
    assert units["410502"]["code"] == "C-410502" and units["4"]["parent"] == "RW"
