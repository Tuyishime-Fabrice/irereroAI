"""PLAN: hand-checked formulas, the priority index, rank stability and the 2026 estimate."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from irerero.config import PRESETS, SIMULATED
from irerero.data.sources.osm import Network
from irerero.plan import distance, gap, priority
from irerero.plan.estimate import estimate


@pytest.mark.parametrize(
    ("target", "children", "attending", "places", "rooms", "caregivers"),
    [
        (0.65, 1000, 300, 350, 12, (12, 24)),  # 650 - 300; 350/30 = 11.7; 350/15 = 23.3
        (0.65, 100, 0, 65, 3, (3, 5)),  # 0.65 * 100 is 65.000...01 in floating point
        (0.65, 1000, 700, 0, 0, (0, 0)),  # already above target
        (0.65, 1001, 300, 351, 12, (12, 24)),  # ceil(650.65) = 651
        (0.50, 60, 0, 30, 1, (1, 2)),  # exactly one room
        (0.50, 62, 0, 31, 2, (2, 3)),  # one child over: a second room
    ],
)
def test_needs_hand_checked(target, children, attending, places, rooms, caregivers):
    assert gap.places(target, children, attending) == places
    assert gap.rooms(places) == rooms
    assert gap.caregivers(places) == caregivers
    frame = pd.DataFrame({"children_3_5": [children], "attending": [attending]})
    row = gap.needs(frame, target).iloc[0]
    assert (row.places, row.rooms, row.caregivers_low, row.caregivers_high) == (
        places,
        rooms,
        *caregivers,
    )


def test_percentiles_and_score():
    comps = pd.DataFrame(
        {"volume": [10, 20, 30], "equity": [0.9, 0.5, 0.1], "poverty": [0.2, 0.2, 0.2]},
        index=["a", "b", "c"],
    )
    pct = priority.percentiles(comps)
    assert pct.volume.tolist() == pytest.approx([1 / 3, 2 / 3, 1])
    assert pct.poverty.tolist() == pytest.approx([2 / 3] * 3)  # ties share the average rank
    score = priority.score(pct, {"volume": 1, "equity": 0, "poverty": 0, "peer_gap": 0})
    assert score.idxmax() == "c"


def test_missing_component_weight_is_shared():
    weights = dict(
        zip(("volume", "equity", "peer_gap", "poverty"), PRESETS["Balanced"], strict=True)
    )
    used = priority.normalise(weights, ["volume", "equity", "poverty"])
    assert sum(used.values()) == pytest.approx(1)
    assert used["volume"] == pytest.approx(0.30 / 0.80)
    assert "peer_gap" not in used


def test_stability_dominant_sector_always_top():
    pct = pd.DataFrame(
        {"volume": [1.0, 0.5, 0.4, 0.3, 0.2], "equity": [1.0, 0.2, 0.5, 0.4, 0.3]},
        index=list("abcde"),
    )
    stab = priority.stability(pct, {"volume": 0.5, "equity": 0.5}, draws=300)
    assert stab["a"] == 1.0
    assert stab.sum() == pytest.approx(3.0)  # three places in the top 3 per draw
    assert priority.stability_label(stab["a"]) == "stable"


def test_stability_is_reproducible():
    pct = pd.DataFrame(np.random.default_rng(1).random((12, 4)), columns=list("wxyz"))
    weights = dict.fromkeys("wxyz", 0.25)
    pd.testing.assert_series_equal(
        priority.stability(pct, weights), priority.stability(pct, weights)
    )


def test_straight_line_distance_share(empty_raw):
    """A 4 km square with one school in a corner: most of it is more than 1 km away."""
    lon0, lat0 = 30.0, -2.0
    d = 4000 / 111_320
    sectors = gpd.GeoDataFrame(
        {"geo_id": ["S"], "geometry": [box(lon0, lat0 - d, lon0 + d, lat0)]}, crs=4326
    )
    corner = Network(
        schools=pd.DataFrame({"lon": [lon0], "lat": [lat0]}), status=SIMULATED, real=False
    )
    row = distance.far_shares(sectors, corner, raw=empty_raw).iloc[0]
    # quarter circle of radius 1 km over a 16 km² square: pi/4 / 16 = 4.9% within reach
    assert row.far_share == pytest.approx(1 - np.pi / 64, abs=0.03)
    assert row.distance_method == distance.STRAIGHT
    assert row.children_spread == "even grid"

    centre = Network(
        schools=pd.DataFrame({"lon": [lon0 + d / 2], "lat": [lat0 - d / 2]}),
        status=SIMULATED,
        real=False,
    )
    assert distance.far_shares(sectors, centre, raw=empty_raw).far_share.iat[0] < row.far_share


def test_road_distance_uses_network():
    """Children 800 m from a school in a straight line, but 2 km along the only road."""
    lon0, lat0 = 30.0, -2.0
    m = 1 / 111_320
    nodes = {1: (lon0, lat0), 2: (lon0, lat0 - 1000 * m), 3: (lon0 + 800 * m, lat0 - 1000 * m),
             4: (lon0 + 800 * m, lat0)}  # fmt: skip
    network = Network(
        schools=pd.DataFrame({"lon": [lon0], "lat": [lat0]}),
        nodes=nodes,
        edges=[(1, 2), (2, 3), (3, 4)],
    )
    schools_xy = distance._metric(np.array([lon0]), np.array([lat0]))
    road = distance.RoadDistance(network, schools_xy)
    child = distance._metric(np.array([lon0 + 800 * m]), np.array([lat0]))
    walk, near = road.query(child)
    assert near[0]
    assert np.isinf(walk[0])  # 2.8 km along the road: beyond the 1 km limit


def test_estimate_calibrates_to_district_totals(inputs):
    from irerero.plan.estimate import children_by_district

    est = estimate(inputs)
    assert len(est) == 416
    totals = children_by_district(inputs, 2026).children_3_5
    sums = est.groupby("district_id").children_3_5.sum()
    assert np.allclose(sums, totals.loc[sums.index], rtol=0.001)
    assert (est.low <= est.children_3_5).all()
    assert (est.children_3_5 <= est.high).all()
    assert est.attendance_rate.between(0, 1).all()
    assert set(est.status) == {SIMULATED}  # built from simulated inputs


def test_a_real_census_is_never_moved_by_a_simulated_yearbook(inputs):
    """Census and projections real, yearbook still simulated: the 2022 rates stay as they are
    (no simulated trend on real figures), and the estimate is not labelled simulated."""
    from dataclasses import replace

    from irerero.config import MODEL

    real = replace(
        inputs,
        census_sectors=replace(inputs.census_sectors, real=True),
        projections=replace(inputs.projections, real=True),
    )
    est = estimate(real).set_index("geo_id")
    assert set(est.status) == {MODEL}
    assert np.allclose(est.attendance_rate, est.attendance_rate_2022.clip(upper=0.98), atol=1e-4)
    assert "not moved by MINEDUC" in est.method.iloc[0]


def test_the_mineduc_trend_moves_attendance_only_when_switched_on(inputs, monkeypatch):
    from irerero.plan import estimate as module

    off = estimate(inputs).set_index("geo_id")
    assert np.allclose(off.attendance_rate, off.attendance_rate_2022.clip(upper=0.98), atol=1e-4)
    assert "not comparable by district" in off.method.iloc[0]
    monkeypatch.setattr(module, "MINEDUC_TREND_ON_CENSUS", True)
    on = module.estimate(inputs).set_index("geo_id")  # all simulated: the demo trend applies
    assert "moved by the MINEDUC trend" in on.method.iloc[0]
    assert not np.allclose(on.attendance_rate, off.attendance_rate)


def test_projected_children_3_5_are_used_when_the_projections_carry_them(inputs):
    from dataclasses import replace

    from irerero.plan.estimate import children_by_district

    frame = inputs.projections.frame.assign(children_3_5=lambda f: (f.population * 0.08).round())
    direct = replace(inputs, projections=replace(inputs.projections, frame=frame))
    totals = children_by_district(direct, 2026).children_3_5
    expected = frame[frame.year == 2026].set_index("geo_id").children_3_5
    assert np.allclose(totals, expected.loc[totals.index])
    est = estimate(direct)
    sums = est.groupby("district_id").children_3_5.sum()
    assert np.allclose(sums, totals.loc[sums.index], rtol=0.001)
    assert "NISR projected children aged 3-5" in est.method.iloc[0]
