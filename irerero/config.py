"""Fixed parameters, each with where it comes from. Change them here, nowhere else."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"
DEMO = DATA / "demo"
CONTENT = ROOT / "content"

SEED = 2026
ESTIMATE_YEAR = 2026

# Definition shown on every screen. Census "nursery school attendance" may leave out
# home-based ECD, so census, MINEDUC and NCDA enrolment are never added together.
DEFINITION = (
    "Formal pre-primary: children aged 3 to 5 attending nursery or pre-primary school, as "
    "counted by the 2022 Census (Table 2.5) and MINEDUC. Home-based ECD may not be included."
)


@dataclass(frozen=True)
class Norm:
    value: float
    citation: str


# National ECD Standards 2024 (NCDA). Encoded as parameters, cited wherever they are used.
STANDARDS = "NCDA, National ECD Standards (2024)"
CHILDREN_PER_ROOM = Norm(30, STANDARDS)
CAREGIVER_RATIO_HIGH = Norm(30, STANDARDS)  # 1 caregiver per 30 children, the upper limit
CAREGIVER_RATIO_LOW = Norm(15, STANDARDS)  # 1 caregiver per 15 children, the recommended
WALKING_DISTANCE_KM = Norm(1.0, STANDARDS)

# NST2 targets for pre-primary enrolment.
NST2 = "Government of Rwanda, Second National Strategy for Transformation (NST2), 2024-2029"
TARGET_2029 = Norm(0.65, NST2)
TARGET_2027 = Norm(0.546, NST2)
TARGET_YEAR = "2028/29"
MILESTONE_YEAR = "2026/27"
YEARBOOK_YEARS = ("2020/21", "2021/22", "2022/23", "2023/24", "2024/25")
PROJECTION_YEARS = ("2025/26", "2026/27", "2027/28", "2028/29")

# Priority index: weights for volume, equity, peer gap, poverty.
PRESETS: dict[str, tuple[float, float, float, float]] = {
    "Reach most children": (0.50, 0.20, 0.15, 0.15),
    "Equity first": (0.15, 0.40, 0.15, 0.30),
    "Balanced": (0.30, 0.30, 0.20, 0.20),
}
COMPONENTS = ("volume", "equity", "peer_gap", "poverty")
COMPONENT_LABELS = {
    "volume": "Children not attending",
    "equity": "Share not attending",
    "peer_gap": "Below similar sectors",
    "poverty": "Poverty",
}
# 2026 estimate. Where a source gives no range, these assumptions set it (documented in
# docs/methodology.md): projection error and drift in sector shares since the 2022 census.
PROJECTION_REL_ERROR = 0.03
SHARE_DRIFT_REL = 0.05
MAX_ATTENDANCE = 0.98  # cap for the projected attendance rate

# Distance layer.
GRID_SPACING_M = 250  # spacing of evenly spread points while WorldPop is missing
SNAP_LIMIT_M = 500  # a point further than this from a road is not on the network
MIN_ROAD_COVERAGE = 0.5  # below this share of points near a road, use straight-line distance
METRIC_CRS = 32735  # WGS 84 / UTM zone 35S covers Rwanda

STABILITY_DRAWS = 500
STABILITY_CONCENTRATION = 40.0  # Dirichlet concentration around the chosen weights
STABILITY_TOP = 3

CONFORMAL_COVERAGE = 0.80
MAX_FEATURES = 6
SIMPLER_WITHIN_PP = 1.0  # keep the simplest model within 1 point of the best MAE

SUPPRESS_BELOW = 10  # exports show cells under 10 children as "fewer than 10"

# Status of every number, shown on hover and in exports.
OBSERVED = "observed"
PUBLISHED = "published estimate"
MODEL = "model estimate"
USER = "user input"
SIMULATED = "simulated"
STATUSES = (OBSERVED, PUBLISHED, MODEL, USER, SIMULATED)

# Brand colours from the IrereroAI logo, plus a colour-blind-safe status set (Okabe-Ito).
NAVY = "#033665"
GREEN = "#18977A"
GOLD = "#ECA837"
INK = "#0F1B2A"
MUTED = "#5B6B7C"
SIMULATED_RED = "#B42318"
STATUS_COLOURS = {
    "on track": "#009E73",
    "at risk": "#E69F00",
    "off track": "#D55E00",
}
BOTTLENECK_COLOURS = {
    "SUPPLY": "#0072B2",
    "DEMAND": "#E69F00",
    "CAPACITY": "#CC79A7",
    "WELLBEING": "#D55E00",
    "NONE": "#009E73",
}
