"""DIAGNOSE: peer model validation, conformal intervals, fallback, Moran's I and the rules."""

import numpy as np
import pandas as pd
import pytest

from irerero.config import PEER_FEATURES
from irerero.diagnose import moran, peer, rules


def synthetic(n_districts=12, per=8, signal=1.0, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = n_districts * per
    x = rng.normal(size=(n, len(PEER_FEATURES)))
    y = 0.3 + signal * 0.08 * x[:, 0] + signal * 0.04 * x[:, 1] + rng.normal(0, 0.02, n)
    frame = pd.DataFrame(x, columns=list(PEER_FEATURES))
    frame["attendance_2022"] = np.clip(y, 0.01, 0.99)
    frame["children_3_5_census"] = rng.integers(500, 3000, n)
    frame["district_id"] = np.repeat([f"D{i}" for i in range(n_districts)], per)
    frame["province"] = np.repeat([f"P{i % 3}" for i in range(n_districts)], per)
    frame.index = [f"S{i}" for i in range(n)]
    return frame


def test_model_beats_baselines_when_there_is_signal():
    result = peer.fit(synthetic())
    assert result.chosen == "linear"  # simplest within 1 point of the best
    assert not result.fallback
    assert result.metrics["linear"]["mae_pp"] < result.metrics["district_mean"]["mae_pp"]
    assert set(result.metrics) == set(peer.ORDER)
    assert result.drivers["S0"][0]["feature"] in PEER_FEATURES
    assert len(result.drivers["S0"]) == 3


def test_fallback_when_features_carry_no_signal():
    frame = synthetic(signal=0.0)
    # give districts their own levels, so the district mean is the best predictor
    offsets = {
        d: o for d, o in zip(frame.district_id.unique(), np.linspace(0.1, 0.6, 12), strict=True)
    }
    frame["attendance_2022"] = frame.district_id.map(offsets) + np.random.default_rng(1).normal(
        0, 0.01, len(frame)
    )
    result = peer.fit(frame)
    assert result.fallback
    assert result.chosen in peer.BASELINES
    assert all(not d for d in result.drivers.values())


def test_conformal_coverage_close_to_target():
    result = peer.fit(synthetic(n_districts=20, per=10))
    assert 0.78 <= result.diagnostics["coverage"] <= 0.9
    assert peer.conformal_halfwidth(np.arange(1, 11) / 100, 0.8) == pytest.approx(0.09)


def test_out_of_fold_predictions_ignore_own_district():
    frame = synthetic()
    base = peer.fit(frame).output.expected
    changed = frame.copy()
    changed.loc[changed.district_id == "D0", "attendance_2022"] += 0.3
    after = peer.fit(changed).output.expected
    d0 = frame.index[frame.district_id == "D0"]
    assert np.allclose(base[d0], after[d0])  # the linear model never saw D0 when predicting it


def test_morans_i_detects_clustering():
    # a line of 50 cells, each touching the next
    pairs = [(i, i + 1) for i in range(49)]
    smooth = moran.morans_i(np.linspace(0, 1, 50), pairs, permutations=199)
    noise = moran.morans_i(np.random.default_rng(1).normal(size=50), pairs, permutations=199)
    assert smooth["morans_i"] > 0.8
    assert smooth["p_value"] < 0.05
    assert abs(noise["morans_i"]) < 0.3
    assert noise["p_value"] > 0.05


ROW = {
    "attendance_rate": 0.30,
    "children_3_5": 1000,
    "attending": 300,
    "far_share": 0.10,
    "access_nonattendance": 0.8,
    "observed": 0.30,
    "low": 0.20,
    "capacity": 0.5,
    "wellbeing": 0.5,
    "home_water": 0.5,
    "home_sanitation": 0.5,
    "fallback": False,
}


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"attendance_rate": 0.70}, "NONE"),
        ({"far_share": 0.45}, "SUPPLY"),
        ({"observed": 0.15}, "DEMAND"),
        ({"capacity": 0.9}, "CAPACITY"),
        ({"wellbeing": 0.8}, "WELLBEING"),
        ({"home_water": 0.9}, "WELLBEING"),
        ({}, "UNCLEAR"),  # below target with no rule applying: review locally, no guess
        # far from school but a small gap, so no rule applies: unclear, not a guessed Supply
        ({"far_share": 0.45, "access_nonattendance": 0.3, "observed": 0.1}, "UNCLEAR"),
    ],
)
def test_bottleneck_rules(change, expected):
    main, action, reasons = rules.bottleneck({**ROW, **change}, 0.65)
    assert main == expected
    assert action
    assert reasons


def test_capacity_action_gives_caregiver_numbers():
    _, action, _ = rules.bottleneck({**ROW, "capacity": 0.9}, 0.65)
    assert "12–24" in action  # 350 places: 1:30 -> 12, 1:15 -> 24


def test_demand_needs_a_nearby_school():
    main, _, _ = rules.bottleneck({**ROW, "far_share": 0.5, "observed": 0.1}, 0.65)
    assert main == "SUPPLY"


def test_secondary_flags_are_listed():
    _, _, reasons = rules.bottleneck({**ROW, "far_share": 0.5, "capacity": 0.9}, 0.65)
    assert any("CAPACITY" in r for r in reasons)


def test_every_bottleneck_that_applies_is_listed_main_first():
    flags, _ = rules.bottlenecks({**ROW, "far_share": 0.5, "capacity": 0.9}, 0.65)
    assert [name for name, _ in flags] == ["SUPPLY", "CAPACITY"]
    assert all(action for _, action in flags)  # each with its own action
    assert rules.bottleneck({**ROW, "far_share": 0.5, "capacity": 0.9}, 0.65)[0] == "SUPPLY"


def test_unclear_does_not_guess_a_cause():
    flags, reasons = rules.bottlenecks(ROW, 0.65)
    assert flags == [(flags[0][0], flags[0][1])] and flags[0][0] == "UNCLEAR"
    assert "review locally" in flags[0][1]
    assert "No rule points to a clear cause." in reasons


def test_built_diagnosis(tables):
    diagnosis = tables["diagnosis"]
    assert len(diagnosis) == 416
    assert set(diagnosis.bottleneck) <= {
        "SUPPLY",
        "DEMAND",
        "CAPACITY",
        "WELLBEING",
        "NONE",
        "UNCLEAR",
    }
    run = tables["model_run"]
    assert run.chosen.sum() == 1
    chosen = run[run.chosen].metrics.iat[0]
    assert {"coverage", "residual_moran", "mae_by_province"} <= set(chosen)
