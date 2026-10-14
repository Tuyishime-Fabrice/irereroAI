"""Descriptions of the Phase 1 baselines, written to model_version when the demo is seeded."""

from irerero_engine.coverage import (
    DEFAULT_CATCHMENT_MINUTES,
    DEFAULT_METRES_PER_MINUTE,
    StraightLineCoverage,
)
from irerero_engine.explain import TemplateExplainer
from irerero_engine.optimizer import BASE_VALUE, SUPPORT_FACTOR, GreedyOptimizer

BASELINES: tuple[dict[str, object], ...] = (
    {
        "id": StraightLineCoverage.version,
        "component": "coverage",
        "description": "Straight-line catchments with an adjustable walking speed; children "
        "matched to the nearest centres until each is full.",
        "params": {
            "catchment_minutes": DEFAULT_CATCHMENT_MINUTES,
            "metres_per_minute": DEFAULT_METRES_PER_MINUTE,
        },
    },
    {
        "id": GreedyOptimizer.version,
        "component": "optimizer",
        "description": "Greedy maximal coverage: highest weighted benefit per franc within the "
        "budget, respecting rejected sites.",
        "params": {"base_value": BASE_VALUE, "support_factor": SUPPORT_FACTOR},
    },
    {
        "id": TemplateExplainer.version,
        "component": "explainer",
        "description": "Template explanations in English and Kinyarwanda from drivers and numbers.",
        "params": {},
    },
)
