"""Descriptions of the Phase 1 baselines, written to model_version when the demo is seeded."""

from irerero_engine.coverage import CATCHMENT_STEPS, DEFAULT_CATCHMENT_MINUTES, CatchmentCoverage
from irerero_engine.explain import TemplateExplainer
from irerero_engine.need import (
    CENSUS_DRIFT,
    DISTRICT_TO_SECTOR,
    MIN_SECTOR_HALF_WIDTH,
    LayeredNeedEstimator,
)
from irerero_engine.optimizer import BASE_VALUE, SUPPORT_FACTOR, GreedyOptimizer
from irerero_engine.travel import DEFAULT_DETOUR, DEFAULT_METRES_PER_MINUTE

BASELINES: tuple[dict[str, object], ...] = (
    {
        "id": LayeredNeedEstimator.version,
        "component": "need",
        "description": "Official values where their files are loaded (census child counts, RDHS "
        "stunting, LFS childcare barrier), the simulated estimate everywhere else. A sector "
        "takes its district's survey value with a wider interval.",
        "params": {
            "census_drift": CENSUS_DRIFT,
            "district_to_sector": DISTRICT_TO_SECTOR,
            "min_sector_half_width": MIN_SECTOR_HALF_WIDTH,
        },
    },
    {
        "id": CatchmentCoverage.version,
        "component": "coverage",
        "description": "Walking-time catchments precomputed by the build, along roads and paths "
        "when the OpenStreetMap extract is loaded and otherwise estimated from straight-line "
        "distance; children matched to the nearest places until each is full.",
        "params": {
            "catchment_minutes": DEFAULT_CATCHMENT_MINUTES,
            "steps": list(CATCHMENT_STEPS),
            "metres_per_minute": DEFAULT_METRES_PER_MINUTE,
            "detour": DEFAULT_DETOUR,
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
