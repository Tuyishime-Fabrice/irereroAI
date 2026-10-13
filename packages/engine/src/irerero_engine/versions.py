"""Descriptions of the Phase 1 baselines, written to model_version when the demo is seeded."""

from irerero_engine.coverage import (
    DEFAULT_CATCHMENT_MINUTES,
    DEFAULT_METRES_PER_MINUTE,
    StraightLineCoverage,
)
from irerero_engine.early_warning import (
    DROP_POINTS,
    DROP_Z,
    MIN_HISTORY,
    MISSING_CRITICAL,
    MISSING_WARNING,
    RuleBasedEarlyWarning,
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
        "id": RuleBasedEarlyWarning.version,
        "component": "early_warning",
        "description": "Rules against each centre's own history: attendance z-score, missing "
        "reports, overcrowding, water and closure.",
        "params": {
            "drop_z": DROP_Z,
            "drop_points": DROP_POINTS,
            "min_history_weeks": MIN_HISTORY,
            "missing_warning_weeks": MISSING_WARNING,
            "missing_critical_weeks": MISSING_CRITICAL,
        },
    },
    {
        "id": TemplateExplainer.version,
        "component": "explainer",
        "description": "Template explanations in English and Kinyarwanda from drivers and numbers.",
        "params": {},
    },
)
