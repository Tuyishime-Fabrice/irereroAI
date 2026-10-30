"""Five factors and the bottleneck rules.

Each factor is a national percentile, 1 = worst. Sector factors (access, home environment,
poverty where published) rank sectors; district factors (capacity, wellbeing) rank the 30
districts and are shown as district context, never as sector values.

    Condition                                           Bottleneck   Action
    at or above target                                  NONE         monitor
    large gap and >= 30% of children beyond 1 km        SUPPLY       build or expand rooms
    school nearby, attendance below the peer interval   DEMAND       parent outreach
    weak teacher ratios or qualifications (district)    CAPACITY     recruit and train caregivers
    high stunting or poor water and sanitation          WELLBEING    nutrition and WASH links
    below target, none of the above                     SUPPLY       expand nearby schools

"Large gap": non-attendance in the national top half (access_nonattendance >= 0.5).
The first rule that applies is the main bottleneck; the others are listed as reasons too.
"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from irerero.config import FAR_SHARE, LARGE_GAP, WEAK_FACTOR
from irerero.plan import gap

FACTORS = ("access", "capacity", "wellbeing", "home", "poverty")
FACTOR_LABELS = {
    "access": "Access",
    "capacity": "Capacity",
    "wellbeing": "Wellbeing",
    "home": "Home environment",
    "poverty": "Poverty",
}
FACTOR_LEVEL = {
    "access": "sector",
    "capacity": "district context",
    "wellbeing": "district context",
    "home": "sector",
    "poverty": "sector or district",
}
COURSES = {
    "CAPACITY": "ECD Standards essentials",
    "WASH": "Hygiene and WASH routines",
    "NUTRITION": "Nutrition and growth monitoring referral",
}


def _pct(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, method="average")


def _mean(parts: list[pd.Series]) -> pd.Series:
    kept = [p for p in parts if p.notna().any()]
    if not kept:
        return pd.Series(np.nan, index=parts[0].index)
    return pd.concat(kept, axis=1).mean(axis=1)


def factors(
    features: pd.DataFrame, training_completion: Mapping[str, float] | None = None
) -> pd.DataFrame:
    """Factor scores (0 to 1, higher = worse) and their parts, per sector."""
    f = features
    out = pd.DataFrame(index=f.index)
    out["access_nonattendance"] = _pct(f.nonattendance)
    out["access_distance"] = _pct(f.far_share)
    out["access"] = _mean([out.access_nonattendance, out.access_distance])

    districts = f.groupby("district_id")[
        ["pupils_per_teacher", "pupils_per_classroom", "qualified_share", "stunting"]
    ].first()
    cap = pd.DataFrame(
        {
            "capacity_teacher_ratio": _pct(districts.pupils_per_teacher),
            "capacity_classroom_ratio": _pct(districts.pupils_per_classroom),
            "capacity_unqualified": _pct(1 - districts.qualified_share),
        }
    )
    if training_completion:
        cap["capacity_training_gap"] = 1 - pd.Series(training_completion).reindex(cap.index)
    cap["capacity"] = cap.mean(axis=1)
    for column in cap.columns:
        out[column] = f.district_id.map(cap[column])
    out["wellbeing"] = f.district_id.map(_pct(districts.stunting))

    out["home_water"] = _pct(1 - f.water_share)
    out["home_sanitation"] = _pct(1 - f.sanitation_share)
    out["home_education"] = _pct(1 - f.women_secondary_share)
    out["home"] = _mean([out.home_water, out.home_sanitation, out.home_education])
    out["poverty"] = _pct(f.poverty)
    return out


def bottleneck(row: Mapping, target: float) -> tuple[str, str, list[str]]:
    """(bottleneck, intervention, reasons) for one sector. `row` holds attendance_rate,
    children_3_5, attending, far_share, access_nonattendance, observed, low, capacity,
    wellbeing, home_water, home_sanitation and fallback."""
    rate = float(row["attendance_rate"])
    places = gap.places(target, row["children_3_5"], row["attending"])
    rooms = gap.rooms(places)
    lo, hi = gap.caregivers(places)
    far = row.get("far_share")
    reasons: list[str] = []
    flags: list[tuple[str, str]] = []

    if rate >= target:
        return (
            "NONE",
            "Monitor: estimated attendance is at or above the target.",
            [f"Estimated attendance {rate:.0%} vs target {target:.0%}."],
        )
    reasons.append(
        f"Estimated attendance {rate:.0%} vs target {target:.0%}: {places:,} places short."
    )
    large = float(row.get("access_nonattendance", 1.0)) >= LARGE_GAP
    if far is not None and far == far and far >= FAR_SHARE and large:
        reasons.append(f"{far:.0%} of children aged 3 to 5 live more than 1 km from a school.")
        flags.append(
            (
                "SUPPLY",
                f"Build or expand rooms: about {rooms} rooms for {places:,} places, sited where "
                "children are far from a school.",
            )
        )
    observed, low = row.get("observed"), row.get("low")
    if (
        (far is None or far != far or far < FAR_SHARE)
        and observed is not None
        and low is not None
        and observed == observed
        and observed < low
    ):
        peers = "the district average" if row.get("fallback") else "similar sectors"
        nearby = (
            "A school is nearby, but attendance"
            if far is not None and far == far
            else "Distance to a school is not known (no complete school list); attendance"
        )
        reasons.append(
            f"{nearby} ({observed:.0%} in 2022) is below the range expected from {peers} "
            f"({low:.0%} or more)."
        )
        flags.append(("DEMAND", "Parent outreach; check fees and awareness."))
    capacity = row.get("capacity")
    if capacity is not None and capacity == capacity and capacity >= WEAK_FACTOR:
        reasons.append(
            "District context: teacher ratios or qualifications are among the weakest "
            f"quarter nationally (capacity score {capacity:.2f})."
        )
        flags.append(
            (
                "CAPACITY",
                f"Recruit and train caregivers: {lo}–{hi} for the places needed (1:30 to 1:15); "
                f"assign the LEARN course '{COURSES['CAPACITY']}'.",
            )
        )
    wellbeing = row.get("wellbeing")
    wash = max(
        (
            v
            for v in (row.get("home_water"), row.get("home_sanitation"))
            if v is not None and v == v
        ),
        default=float("nan"),
    )
    if (wellbeing is not None and wellbeing == wellbeing and wellbeing >= WEAK_FACTOR) or (
        wash == wash and wash >= WEAK_FACTOR
    ):
        if wellbeing is not None and wellbeing == wellbeing and wellbeing >= WEAK_FACTOR:
            reasons.append("District context: stunting is among the highest quarter nationally.")
        if wash == wash and wash >= WEAK_FACTOR:
            reasons.append("Water or sanitation access is among the weakest quarter nationally.")
        flags.append(
            (
                "WELLBEING",
                "Link with nutrition and WASH programmes; assign the LEARN courses "
                f"'{COURSES['NUTRITION']}' and '{COURSES['WASH']}'.",
            )
        )
    if not flags:
        flags.append(
            (
                "SUPPLY",
                f"Expand places at nearby schools: about {rooms} rooms for {places:,} places.",
            )
        )
    main, action = flags[0]
    others = [name for name, _ in flags[1:] if name != main]
    if others:
        reasons.append("Also flagged: " + ", ".join(dict.fromkeys(others)) + ".")
    return main, action, reasons


def diagnose(frame: pd.DataFrame, target: float) -> pd.DataFrame:
    """Adds bottleneck, intervention and reasons to a frame with the columns `bottleneck`
    reads."""
    results = [bottleneck(row, target) for row in frame.to_dict(orient="records")]
    out = frame.copy()
    out["bottleneck"] = [r[0] for r in results]
    out["intervention"] = [r[1] for r in results]
    out["reasons"] = [r[2] for r in results]
    return out
