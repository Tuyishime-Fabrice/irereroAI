"""Run the peer model and the bottleneck rules over the built tables."""

import pandas as pd

from irerero.config import MODEL, SIMULATED, TARGET_2029
from irerero.diagnose import moran, peer, rules
from irerero.diagnose.features import sector_features, simulated_features
from irerero.pipeline.inputs import Inputs


def run(inputs: Inputs, tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    features = sector_features(tables["observation"], tables["geo_unit"], tables["estimate_2026"])
    result = peer.fit(features)
    # the diagnosis rules read every factor; the peer model only census attendance and the
    # features it kept (none when it falls back to the district average)
    status = SIMULATED if features.inputs_simulated.any() else MODEL
    used = {"attendance_2022", *([] if result.fallback else result.features)}
    simulated = simulated_features(tables["observation"], tables["estimate_2026"])
    peer_status = SIMULATED if used & simulated else MODEL

    residuals = result.output.observed - result.output.expected
    result.diagnostics["residual_moran"] = moran.residual_moran(inputs.sectors, residuals)
    runs = pd.DataFrame(
        [
            {
                "model_id": name,
                "chosen": name == result.chosen,
                "metrics": {
                    **metrics,
                    "label": peer.MODEL_LABELS[name],
                    **(
                        {
                            "fallback": result.fallback,
                            "features": result.features,
                            "importance_pp": result.importance,
                            "interval_halfwidth_pp": round(result.interval_halfwidth * 100, 2),
                            **result.diagnostics,
                        }
                        if name == result.chosen
                        else {}
                    ),
                },
            }
            for name, metrics in result.metrics.items()
        ]
    )
    output = result.output.assign(
        model_id="district_mean" if result.fallback else result.chosen,
        drivers=[result.drivers.get(g, []) for g in result.output.index],
        status=peer_status,
    )
    output = output.rename_axis("geo_id").reset_index()

    scores = rules.factors(features)
    est = tables["estimate_2026"].set_index("geo_id")
    frame = scores.join(est[["attendance_rate", "children_3_5", "attending", "far_share"]])
    frame = frame.join(output.set_index("geo_id")[["observed", "low"]])
    frame["fallback"] = result.fallback
    diagnosed = rules.diagnose(frame.reset_index(names="geo_id"), TARGET_2029.value)
    part_columns = [c for c in scores.columns if c not in rules.FACTORS]
    diagnosis = pd.DataFrame(
        {
            "geo_id": diagnosed.geo_id,
            **{f: diagnosed[f] for f in rules.FACTORS},
            "bottleneck": diagnosed.bottleneck,
            "intervention": diagnosed.intervention,
            "reasons": diagnosed.reasons,
            "details": [
                {c: (None if pd.isna(v) else round(float(v), 4)) for c, v in row.items()}
                for row in diagnosed[part_columns].to_dict(orient="records")
            ],
            "status": status,
        }
    )
    return {"model_run": runs, "model_output": output, "diagnosis": diagnosis}
