"""One row per sector with every indicator DIAGNOSE uses, from the observation, geo_unit and
estimate_2026 tables. District values are mapped onto their sectors and marked as district
context; they are never shown as sector values."""

import numpy as np
import pandas as pd

from irerero.config import SIMULATED, YEARBOOK_YEARS

# indicator -> level it is measured at
LEVEL = {
    "attendance_2022": "sector",
    "nonattendance": "sector",
    "far_share": "sector",
    "urban_share": "sector",
    "women_secondary_share": "sector",
    "water_share": "sector",
    "sanitation_share": "sector",
    "electricity_share": "sector",
    "log_density": "sector",
    "poverty": "sector or district",
    "pupils_per_teacher": "district",
    "pupils_per_classroom": "district",
    "qualified_share": "district",
    "stunting": "district",
}
LABELS = {
    "attendance_2022": "Attendance, census 2022",
    "nonattendance": "Children 3-5 not attending (2026)",
    "far_share": "Children more than 1 km from a school",
    "urban_share": "Urban population",
    "women_secondary_share": "Women with secondary education",
    "water_share": "Households with improved water",
    "sanitation_share": "Households with improved sanitation",
    "electricity_share": "Households with electricity",
    "log_density": "Children per km² (log)",
    "poverty": "Poverty rate",
    "pupils_per_teacher": "Pre-primary pupils per teacher",
    "pupils_per_classroom": "Pre-primary pupils per classroom",
    "qualified_share": "Qualified pre-primary teachers",
    "stunting": "Stunting, children under 5",
    "training_completion": "Caregivers who completed required training (LEARN)",
}


# where each indicator comes from; "estimate" and "distance" are IrereroAI's own layers
SOURCES = {
    "attendance_2022": "census_2022",
    "nonattendance": "estimate",
    "far_share": "distance",
    "urban_share": "census_2022",
    "women_secondary_share": "census_2022",
    "water_share": "census_2022",
    "sanitation_share": "census_2022",
    "electricity_share": "census_2022",
    "log_density": "census_2022",
    "poverty": "eicv7",
    "pupils_per_teacher": "yearbook",
    "pupils_per_classroom": "yearbook",
    "qualified_share": "yearbook",
    "stunting": "rdhs_2025",
}


def simulated_features(obs: pd.DataFrame, estimates: pd.DataFrame) -> set[str]:
    """The indicators that rest on a simulated stand-in."""
    sources = set(obs[obs.status == SIMULATED].source_id)
    if (estimates.status == SIMULATED).any():
        sources |= {"estimate", "distance"}
    if estimates.distance_method.astype(str).str.contains("simulated").any():
        sources.add("distance")
    return {feature for feature, source in SOURCES.items() if source in sources}


def _wide(obs: pd.DataFrame, period: str | None = None) -> pd.DataFrame:
    rows = obs if period is None else obs[obs.reference_period == period]
    rows = rows.sort_values("reference_period").groupby(["geo_id", "indicator_id"]).tail(1)
    return rows.pivot(index="geo_id", columns="indicator_id", values="value")


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return frame[name] if name in frame else pd.Series(np.nan, index=frame.index)


def sector_features(
    obs: pd.DataFrame, units: pd.DataFrame, estimates: pd.DataFrame
) -> pd.DataFrame:
    sectors = units[units.level == "sector"].set_index("geo_id")
    census = _wide(obs[obs.source_id == "census_2022"]).reindex(sectors.index)
    est = estimates.set_index("geo_id").reindex(sectors.index)
    district = sectors.parent_id

    out = pd.DataFrame(index=sectors.index)
    out["district_id"] = district
    out["province"] = sectors.province
    out["attendance_2022"] = census.attending_3_5 / census.children_3_5
    out["children_3_5_census"] = census.children_3_5
    out["nonattendance"] = 1 - est.attendance_rate
    out["far_share"] = est.far_share
    out["urban_share"] = _col(census, "urban_share")
    out["women_secondary_share"] = _col(census, "women_secondary_share")
    households = _col(census, "households")
    out["water_share"] = _col(census, "hh_improved_water") / households
    out["sanitation_share"] = _col(census, "hh_improved_sanitation") / households
    out["electricity_share"] = _col(census, "hh_electricity") / households
    out["log_density"] = np.log1p(census.children_3_5 / sectors.area_km2)

    poverty = _wide(obs[obs.indicator_id == "poverty_rate"])
    pov = _col(poverty, "poverty_rate")
    out["poverty"] = out.index.map(pov).astype(float)
    out["poverty_level"] = np.where(out.poverty.notna(), "sector", "district")
    out["poverty"] = out.poverty.fillna(district.map(pov).astype(float))

    latest = YEARBOOK_YEARS[-1]
    book = _wide(obs[obs.source_id == "yearbook"], latest)
    out["pupils_per_teacher"] = district.map(book.pp_pupils / book.pp_teachers)
    out["pupils_per_classroom"] = district.map(book.pp_pupils / book.pp_classrooms)
    out["qualified_share"] = district.map(book.pp_teachers_qualified / book.pp_teachers)
    stunting = _wide(obs[obs.indicator_id == "stunting_u5"])
    out["stunting"] = district.map(_col(stunting, "stunting_u5")).astype(float)

    # the rules read every indicator above, so any simulated one makes the diagnosis simulated
    out["inputs_simulated"] = bool(simulated_features(obs, estimates))
    return out
