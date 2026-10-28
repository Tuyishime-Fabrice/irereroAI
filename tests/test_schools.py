"""The provisional school list: parsed record by record (bad records counted, never guessed),
used by the distance layer, labelled provisional everywhere, drawn on the Overview map, and
never used as evidence in the bottleneck rules. Made-up points, not the real file."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from streamlit.testing.v1 import AppTest

from irerero.config import PROVISIONAL, ROOT, SIMULATED
from irerero.data.sources import schools
from irerero.db.models import Base
from irerero.pipeline.build import build
from irerero.pipeline.inputs import school_network
from irerero.plan.frame import distance_status

KIGALI = (30.06, -1.95)


def _feature(lon, lat, **props):
    base = {"school_code": 1, "school_name": "A", "district": "Gasabo", "sector": "Remera",
            "school_category": "PRE_PRIMARY", "school_status": "PRIVATE",
            "preprimary_students_total": 50}  # fmt: skip
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {**base, **props},
    }


def _collection(features):
    return {"type": "FeatureCollection", "features": features}


def _write(raw: Path, features) -> Path:
    folder = raw / "schools"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / schools.FILE).write_text(json.dumps(_collection(features)))
    return folder / schools.FILE


def test_every_record_is_checked_and_bad_ones_are_counted_not_guessed():
    frame, report = schools.parse(
        _collection(
            [
                _feature(*KIGALI, school_code=1),
                _feature(30.1, -2.0, school_code=2, school_name=None, preprimary_students_total=""),
                _feature(-1.95, 30.06, school_code=3),  # swapped: outside Rwanda, left out
                _feature(2.35, 48.85, school_code=4),  # Paris
                _feature("east", -2.0, school_code=5),  # not a number
                {"type": "Feature", "geometry": None, "properties": {"school_code": 6}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [30.0]}},
                "not a feature",
                _feature(*KIGALI, school_code=9),  # same site as school 1
            ]
        )
    )
    assert report.features == 9 and report.loaded == 3 and len(frame) == 3
    assert report.invalid_coordinates == 3 and report.missing_geometry == 2
    assert report.duplicate_points == 1 and report.errors == ["record 8 is not a GeoJSON feature"]
    assert report.missing_properties["school_name"] >= 1
    assert report.missing_properties["preprimary_students_total"] >= 1
    assert frame.preprimary_students_total.isna().sum() == 1  # a blank count stays blank
    assert set(frame.school_id) == {"mineduc-1", "mineduc-2", "mineduc-9"}


def test_a_file_that_is_not_geojson_is_reported(tmp_path):
    frame, report = schools.parse({"type": "Feature"})
    assert frame.empty and "FeatureCollection" in report.errors[0]
    bad = tmp_path / "schools.geojson"
    bad.write_text("{not json")
    frame, report = schools.read(bad)
    assert frame.empty and "could not be read" in report.errors[0]


def test_the_school_list_feeds_the_network_labelled_provisional(tmp_path):
    _write(tmp_path, [_feature(*KIGALI)])
    network = school_network(tmp_path)
    assert network.source == schools.SOURCE and network.status == PROVISIONAL and network.real
    assert len(network.schools) == 1 and not network.edges  # straight line: no roads
    _write(tmp_path, [_feature(2.35, 48.85)])  # nothing usable: the stand-in, and why
    fallback = school_network(tmp_path)
    assert fallback.status == SIMULATED and fallback.report["invalid_coordinates"] == 1


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """A build on the demo bundle plus a made-up school list: one school in each of three
    sectors' centres, so their children are near a listed school."""
    raw = tmp_path_factory.mktemp("raw")
    geo = json.loads((ROOT / "data" / "demo" / "boundaries" / "sectors.geojson").read_text())
    picked = geo["features"][:3]
    from shapely.geometry import shape

    centres = [shape(f["geometry"]).representative_point() for f in picked]
    _write(raw, [_feature(c.x, c.y, school_code=i) for i, c in enumerate(centres)])
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db') / 'db.sqlite'}")
    Base.metadata.create_all(engine)
    out = tmp_path_factory.mktemp("processed")
    tables = build(raw, engine, out)
    return tables, out, [f["properties"]["geo_id"] for f in picked]


def test_the_schools_reach_the_distance_layer_and_are_labelled(built):
    tables, out, near = built
    est = tables["estimate_2026"].set_index("geo_id")
    assert est.distance_method.str.contains("provisional: 3 listed schools").all()
    assert distance_status(est.reset_index()) == PROVISIONAL
    # sectors with a listed school have fewer children beyond 1 km than the rest
    assert est.loc[near, "far_share"].mean() < est.drop(index=near).far_share.mean()
    points = json.loads((out / "schools.geojson").read_text())["features"]
    assert len(points) == 3 and {p["properties"]["status"] for p in points} == {PROVISIONAL}
    report = json.loads((out / "schools_report.json").read_text())
    assert report["loaded"] == 3 and report["invalid_coordinates"] == 0
    sources = tables["source"].set_index("source_id").loaded
    assert sources["schools"] and not sources["osm"]


def test_a_partial_school_list_is_never_evidence_in_the_bottleneck(built):
    tables, _, _ = built
    reasons = tables["diagnosis"].reasons.astype(str)
    assert not reasons.str.contains("1 km").any()  # the upper bound is not "far"
    assert not reasons.str.contains("A school is nearby").any()  # nor "near"


def test_the_overview_draws_the_school_points(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path_factory.mktemp('ui') / 'a.sqlite'}")
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()  # the first run builds, and (re)loads the irerero modules the app uses
    import sys

    data = sys.modules["irerero.ui.data"]
    points = [{"lon": 30.06, "lat": -1.95, "name": "Test nursery school", "district": "Gasabo",
               "sector": "Remera", "pupils": 40, "status": PROVISIONAL,
               "source": schools.SOURCE}]  # fmt: skip
    monkeypatch.setattr(data, "schools", lambda: (points, {"loaded": 1, "features": 1}))
    at.session_state["map-view"] = "Distance to school"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    decks = [d.proto.json for d in at.get("deck_gl_json_chart")]
    drawn = [d for d in decks if "ScatterplotLayer" in d]
    assert drawn and "Test nursery school" in drawn[0]


def test_far_shares_follow_the_listed_schools():
    """A unit check of the method: one school at a sector's centre lowers its far share."""
    from shapely.geometry import box

    from irerero.data.sources.osm import Network
    from irerero.plan.distance import far_shares

    sector = pd.DataFrame({"geo_id": ["S-1"]})
    import geopandas as gpd

    frame = gpd.GeoDataFrame(sector, geometry=[box(30.0, -2.01, 30.02, -1.99)], crs=4326)
    near = Network(schools=pd.DataFrame({"lon": [30.01], "lat": [-2.0]}), real=True)
    far = Network(schools=pd.DataFrame({"lon": [30.5], "lat": [-2.0]}), real=True)
    empty = Path("/nonexistent")
    assert far_shares(frame, near, empty).far_share.iat[0] < 0.5
    assert np.isclose(far_shares(frame, far, empty).far_share.iat[0], 1.0)
