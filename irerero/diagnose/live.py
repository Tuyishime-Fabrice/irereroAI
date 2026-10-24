"""Diagnosis at the planner's target, with LEARN training completion folded into capacity.
Pure pandas over the built tables, shared by the app and the tests."""

from collections.abc import Mapping

import pandas as pd

from irerero.config import MODEL, SIMULATED
from irerero.diagnose import rules
from irerero.diagnose.features import sector_features, simulated_features


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
    out = out.rename(
        columns={"low": "children_low", "high": "children_high", "status": "estimate_status"}
    )
    model = model_output.set_index("geo_id")
    out = out.join(model[["observed", "expected", "low", "high", "drivers"]])
    out["peer_status"] = model.status.reindex(out.index)
    # the rules read every factor: the diagnosis is simulated while any of its inputs is
    simulated = simulated_features(observation, estimate)
    out["status"] = SIMULATED if simulated else MODEL
    out["simulated_inputs"] = [sorted(simulated)] * len(out)  # indicator keys
    chosen = model_run[model_run.chosen]
    out["fallback"] = bool(chosen.metrics.iat[0].get("fallback", False)) if len(chosen) else True
    out = out.reset_index(names="geo_id")
    return rules.diagnose(out, target)
