"""Diagnosis at the planner's target, with LEARN training completion folded into capacity.
Pure pandas over the built tables, shared by the app and the tests."""

from collections.abc import Mapping

import pandas as pd

from irerero.diagnose import rules
from irerero.diagnose.features import sector_features


def frame(
    observation: pd.DataFrame,
    geo_unit: pd.DataFrame,
    estimate: pd.DataFrame,
    model_output: pd.DataFrame,
    model_run: pd.DataFrame,
    target: float,
    training_completion: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    features = sector_features(observation, geo_unit, estimate)
    scores = rules.factors(features, training_completion)
    est = estimate.set_index("geo_id")
    out = features.join(scores, rsuffix="_score")
    out = out.join(est[["children_3_5", "low", "high", "attendance_rate", "attending", "status"]])
    out = out.rename(columns={"low": "children_low", "high": "children_high"})
    model = model_output.set_index("geo_id")
    out = out.join(model[["observed", "expected", "low", "high", "drivers"]])
    chosen = model_run[model_run.chosen]
    out["fallback"] = bool(chosen.metrics.iat[0].get("fallback", False)) if len(chosen) else True
    out = out.reset_index(names="geo_id")
    return rules.diagnose(out, target)
