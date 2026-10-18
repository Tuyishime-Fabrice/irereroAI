"""Peer benchmark: what attendance would we expect in a sector, given sectors like it?

Target: census 2022 attendance rate of children aged 3 to 5 (observed). Up to six features
(PEER_FEATURES). Four candidates, compared by leave-one-district-out cross-validation:

    province mean   weighted mean of the other districts' sectors in the same province
    district mean   weighted mean of the other sectors in the same district (leave one sector
                    out; it uses information from the district itself, so it is a strong bar)
    linear          weighted linear regression on standardised features
    lightgbm        small gradient-boosted trees

The simplest candidate within SIMPLER_WITHIN_PP points of the best MAE is kept. If that is a
baseline, no model beats the district mean: the peer gap is dropped from the priority index
and each sector is compared with its district average instead (the fallback).

Expected values are out-of-fold, so a sector's expectation never uses its own district (models)
or its own value (district mean). Intervals are split-conformal at CONFORMAL_COVERAGE.
Drivers are associations, not causes.
"""

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from irerero.config import CONFORMAL_COVERAGE, PEER_FEATURES, SEED, SIMPLER_WITHIN_PP
from irerero.diagnose.features import LABELS

ORDER = ("province_mean", "district_mean", "linear", "lightgbm")  # simplest first
BASELINES = {"province_mean", "district_mean"}
MODEL_LABELS = {
    "province_mean": "Province mean (baseline)",
    "district_mean": "District mean (baseline)",
    "linear": "Weighted linear regression",
    "lightgbm": "LightGBM",
}


@dataclass
class PeerResult:
    chosen: str
    fallback: bool
    features: list[str]
    metrics: dict[str, dict[str, float]]
    output: pd.DataFrame  # geo_id index: observed, expected, low, high
    drivers: dict[str, list[dict[str, Any]]]
    interval_halfwidth: float
    importance: dict[str, float] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _wmean(values: pd.Series, weights: pd.Series) -> float:
    return float(np.average(values, weights=weights)) if weights.sum() > 0 else float("nan")


def _province_mean(y: pd.Series, w: pd.Series, district: pd.Series, province: pd.Series):
    out = pd.Series(np.nan, index=y.index)
    for d in district.unique():
        test = district == d
        same = (province == province[test].iat[0]) & ~test
        train = same if same.any() else ~test
        out[test] = _wmean(y[train], w[train])
    return out


def _district_mean(y: pd.Series, w: pd.Series, district: pd.Series) -> pd.Series:
    total = (y * w).groupby(district).transform("sum")
    weight = w.groupby(district).transform("sum")
    loo = (total - y * w) / (weight - w)
    return loo.fillna(y.groupby(district).transform("mean"))


def _linear():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LinearRegression())


def _lightgbm():
    from lightgbm import LGBMRegressor

    return LGBMRegressor(
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=7,
        min_child_samples=12,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        random_state=SEED,
        verbose=-1,
    )


def _lodo(make, x: pd.DataFrame, y: pd.Series, w: pd.Series, district: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=y.index)
    for d in district.unique():
        test = district == d
        model = make()
        fit = {"linearregression__sample_weight": w[~test]} if hasattr(model, "steps") else {}
        if not fit:
            fit = {"sample_weight": w[~test]}
        model.fit(x[~test], y[~test], **fit)
        out[test] = model.predict(x[test])
    return out


def _metrics(y: pd.Series, pred: pd.Series, w: pd.Series) -> dict[str, float]:
    err = (pred - y).abs() * 100
    return {
        "mae_pp": round(float(err.mean()), 2),
        "weighted_mae_pp": round(float(np.average(err, weights=w)), 2),
        "r2": round(float(r2_score(y, pred)), 3),
    }


def conformal_halfwidth(residuals: np.ndarray, coverage: float = CONFORMAL_COVERAGE) -> float:
    """Split-conformal half-width: the k-th smallest absolute residual, k = ceil((n+1)c)."""
    ordered = np.sort(np.abs(residuals))
    k = min(len(ordered), math.ceil((len(ordered) + 1) * coverage))
    return float(ordered[k - 1])


def _drivers(chosen: str, x: pd.DataFrame, y: pd.Series, w: pd.Series):
    """Per-sector contributions (in points) of each feature to the expectation, relative to
    the average sector, from the model refitted on every sector."""
    if chosen == "linear":
        model = _linear()
        model.fit(x, y, linearregression__sample_weight=w)
        z = model[:-1].transform(x)
        contrib = pd.DataFrame(z * model[-1].coef_, index=x.index, columns=x.columns)
    else:
        import shap

        model = _lightgbm()
        model.fit(x, y, sample_weight=w)
        values = shap.TreeExplainer(model).shap_values(x)
        contrib = pd.DataFrame(values, index=x.index, columns=x.columns)
    return contrib * 100


def fit(features: pd.DataFrame) -> PeerResult:
    data = features[features.attendance_2022.notna()]
    usable = [f for f in PEER_FEATURES if f in data and data[f].notna().any()]
    x = data[usable].astype(float)
    y = data.attendance_2022.astype(float)
    w = data.children_3_5_census.astype(float).fillna(1.0)
    district, province = data.district_id, data.province

    preds = {
        "province_mean": _province_mean(y, w, district, province),
        "district_mean": _district_mean(y, w, district),
    }
    if usable:
        preds["linear"] = _lodo(_linear, x, y, w, district)
        preds["lightgbm"] = _lodo(_lightgbm, x, y, w, district)
    metrics = {name: _metrics(y, p, w) for name, p in preds.items()}
    best = min(m["mae_pp"] for m in metrics.values())
    chosen = next(
        n for n in ORDER if n in metrics and metrics[n]["mae_pp"] <= best + SIMPLER_WITHIN_PP
    )
    fallback = chosen in BASELINES
    expected = preds["district_mean"] if fallback else preds[chosen]
    residual = (y - expected).to_numpy()
    q = conformal_halfwidth(residual)
    output = pd.DataFrame(
        {
            "observed": y,
            "expected": expected,
            "low": (expected - q).clip(0, 1),
            "high": (expected + q).clip(0, 1),
        }
    )

    drivers: dict[str, list[dict[str, Any]]] = {g: [] for g in data.index}
    importance: dict[str, float] = {}
    if not fallback:
        contrib = _drivers(chosen, x, y, w)
        importance = contrib.abs().mean().sort_values(ascending=False).round(2).to_dict()
        for geo_id, row in contrib.iterrows():
            top = row.abs().sort_values(ascending=False).index[:3]
            drivers[geo_id] = [
                {
                    "feature": f,
                    "label": LABELS.get(f, f),
                    "contribution_pp": round(float(row[f]), 1),
                    "value": None if pd.isna(x.at[geo_id, f]) else round(float(x.at[geo_id, f]), 3),
                }
                for f in top
            ]

    inside = (y >= output.low) & (y <= output.high)
    diagnostics: dict[str, Any] = {"coverage": round(float(inside.mean()), 3)}
    err = (expected - y).abs() * 100
    if "urban_share" in data and data.urban_share.notna().any():
        area = np.where(data.urban_share >= 0.5, "urban", "rural")
        diagnostics["mae_by_area"] = err.groupby(area).mean().round(2).to_dict()
        diagnostics["coverage_by_area"] = inside.groupby(area).mean().round(3).to_dict()
    diagnostics["mae_by_province"] = err.groupby(province).mean().round(2).to_dict()
    diagnostics["n_sectors"] = len(data)
    diagnostics["n_districts"] = int(district.nunique())
    return PeerResult(
        chosen=chosen,
        fallback=fallback,
        features=usable,
        metrics=metrics,
        output=output,
        drivers=drivers,
        interval_halfwidth=q,
        importance=importance,
        diagnostics=diagnostics,
    )
