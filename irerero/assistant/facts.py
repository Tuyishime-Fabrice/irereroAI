"""Dashboard figures for the assistant, from the same functions the screens use.

Every function takes the app's own tables and returns plain, JSON-ready values, each block
tagged with its status (observed, published estimate, model estimate, simulated) so the
model can say what is real. Nothing here computes a figure the screens do not.
"""

import difflib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from irerero.config import (
    COMPONENT_LABELS,
    COMPONENTS,
    MILESTONE_YEAR,
    PRESETS,
    PROJECTION_YEARS,
    SIMULATED,
    STABILITY_DRAWS,
    TARGET_2027,
    TARGET_2029,
    TARGET_YEAR,
    YEARBOOK_YEARS,
)
from irerero.diagnose.features import LABELS
from irerero.plan import gap
from irerero.plan.frame import distance_status, ranked, status_of
from irerero.plan.priority import stability_label
from irerero.track import forecast

NATIONAL = forecast.NATIONAL
MAX_LIST = 30


@dataclass
class Tables:
    """The tables the screens read, gathered once per question."""

    sectors: pd.DataFrame
    """irerero.plan.frame.sectors()"""
    forecast: pd.DataFrame
    """the forecast table"""
    diagnosis: pd.DataFrame
    """irerero.diagnose.live.frame() for the current target, with name and district"""
    sources: pd.DataFrame
    """the source table"""
    model_run: pd.DataFrame = field(default_factory=pd.DataFrame)
    plans: Mapping[str, Any] = field(default_factory=dict)
    """district_id -> plan summary (from irerero.track.plans), when available"""

    @property
    def districts(self) -> dict[str, str]:
        rows = self.sectors[["district_id", "district"]].drop_duplicates().sort_values("district")
        return dict(zip(rows.district_id, rows.district, strict=True))


class NotFound(ValueError):
    """A district or sector name that is not in the data, with the closest names."""


def _pct(x: float | None, digits: int = 1) -> float | None:
    return None if x is None or x != x else round(float(x) * 100, digits)


def _int(x: float | None) -> int | None:
    return None if x is None or x != x else round(float(x))


def _status(frame: pd.DataFrame) -> str:
    return status_of(frame)


def find_district(t: Tables, name: str) -> str:
    """district_id for a district name typed by a person (case and spacing ignored)."""
    by_name = {v.casefold(): k for k, v in t.districts.items()}
    key = " ".join(str(name).split()).casefold().removesuffix(" district")
    if key in by_name:
        return by_name[key]
    if key.upper().startswith("D-") and key.upper() in t.districts:
        return key.upper()
    close = difflib.get_close_matches(key, list(by_name), n=3)
    raise NotFound(
        f"No district called '{name}'."
        + (f" Closest: {', '.join(t.districts[by_name[c]] for c in close)}." if close else "")
    )


def find_sector(t: Tables, name: str, district_id: str) -> str:
    rows = t.sectors[t.sectors.district_id == district_id]
    by_name = {v.casefold(): g for g, v in zip(rows.geo_id, rows.name, strict=True)}
    key = " ".join(str(name).split()).casefold().removesuffix(" sector")
    if key in by_name:
        return by_name[key]
    close = difflib.get_close_matches(key, list(by_name), n=3)
    district = t.districts.get(district_id, district_id)
    raise NotFound(
        f"No sector called '{name}' in {district}."
        + (f" Closest: {', '.join(c.title() for c in close)}." if close else "")
        + f" Sectors: {', '.join(sorted(rows.name))}."
    )


def _scope(t: Tables, province: str | None) -> pd.DataFrame:
    if not province or province.casefold().startswith("all"):
        return t.sectors
    rows = t.sectors[t.sectors.province.str.casefold() == province.casefold()]
    if rows.empty:
        known = ", ".join(sorted(t.sectors.province.dropna().unique()))
        raise NotFound(f"No province called '{province}'. Provinces: {known}.")
    return rows


def _track(t: Tables, target: float) -> pd.DataFrame:
    return forecast.summary(t.forecast, target)


def _trend(row: pd.Series) -> dict[str, Any]:
    return {
        f"enrolment_rate_{YEARBOOK_YEARS[-1]}_pct": _pct(row.latest),
        f"projected_{TARGET_YEAR}_pct": _pct(row.projected),
        "projected_80pct_range_pct": [_pct(row.low), _pct(row.high)],
        "status_vs_target": row.status,
        "backtest_error_points": None
        if row.backtest_error_pp != row.backtest_error_pp
        else round(float(row.backtest_error_pp), 1),
    }


def _forecast_status(t: Tables, geo_id: str) -> str:
    rows = t.forecast[t.forecast.geo_id == geo_id]
    return SIMULATED if (rows.status == SIMULATED).any() else "model estimate"


def data_status(t: Tables) -> dict[str, Any]:
    """Which datasets are real files and which are labelled stand-ins."""
    src = t.sources
    real = src[src.loaded.astype(bool)]
    stand_in = src[~src.loaded.astype(bool)]
    out: dict[str, Any] = {
        "real_files": [
            {"dataset": r.title, "period": r.reference_period} for r in real.itertuples()
        ],
        "simulated_stand_ins": [
            {"dataset": r.title, "while_missing": r.notes} for r in stand_in.itertuples()
        ],
        "note": "Values that depend on a stand-in carry the status 'simulated': they show "
        "the method, not the real situation, and are left out of exports by default.",
    }
    if len(t.model_run):
        chosen = t.model_run[t.model_run.chosen].iloc[0]
        m = chosen.metrics
        out["peer_model"] = {
            "chosen": chosen.model_id,
            "validation": "leave-one-district-out cross-validation",
            "mae_points": m.get("mae_pp"),
            "r2": m.get("r2"),
            "interval_coverage": m.get("coverage"),
            "computed_on_simulated_data": bool((t.forecast.status == SIMULATED).any()),
        }
    return out


def overview(t: Tables, target: float, province: str | None = None) -> dict[str, Any]:
    """The Overview screen: KPIs, the 2028/29 outlook and the districts needing places first."""
    scope = _scope(t, province)
    needs = gap.needs(scope, target)
    status = _status(scope)
    children = needs.children_3_5.sum()
    track = _track(t, target)
    in_scope = set(scope.district_id)
    districts = track.drop(index=NATIONAL)
    districts = districts[districts.index.isin(in_scope)]
    by = (
        needs.groupby(["district_id", "district", "province"])
        .agg(
            children=("children_3_5", "sum"),
            attending=("attending", "sum"),
            places=("places", "sum"),
            rooms=("rooms", "sum"),
        )
        .reset_index()
        .sort_values("places", ascending=False)
    )
    nat = track.loc[NATIONAL]
    milestone = t.forecast[
        (t.forecast.geo_id == NATIONAL)
        & (t.forecast.kind == "projected")
        & (t.forecast.year == MILESTONE_YEAR)
    ]
    return {
        "area": province if province and not province.startswith("All") else "Rwanda",
        "target_attendance_pct": _pct(target, 0),
        "estimate_2026": {
            "status": status,
            "source": "IrereroAI 2026 estimate (census 2022 base, calibrated to NISR projections)",
            "children_3_5": _int(children),
            "children_3_5_range": [_int(needs.low.sum()), _int(needs.high.sum())],
            "attending_pre_primary_pct": _pct(needs.attending.sum() / children),
            "attending_children": _int(needs.attending.sum()),
            f"places_needed_for_{_pct(target, 0):g}pct": _int(needs.places.sum()),
            "rooms_at_30_children": _int(needs.rooms.sum()),
            "caregivers_range": [
                _int(needs.caregivers_low.sum()),
                _int(needs.caregivers_high.sum()),
            ],
            "children_more_than_1km_from_school_pct": _pct(
                (needs.far_share * needs.children_3_5).sum() / children, 0
            ),
            "distance_method": needs.distance_method.mode().iat[0] if len(needs) else None,
            "distance_status": distance_status(scope),
        },
        "national_trend": {
            "status": _forecast_status(t, NATIONAL),
            "measure": "gross rate: MINEDUC pre-primary pupils per child aged 3-5, linear trend",
            **_trend(nat),
            f"projected_{MILESTONE_YEAR}_pct": _pct(milestone.value.iat[0])
            if len(milestone)
            else None,
        },
        "districts_by_status": districts.status.value_counts().to_dict(),
        "districts_needing_most_places": [
            {
                "rank": i,
                "district": r.district,
                "province": r.province,
                "places_needed": int(r.places),
                "rooms": int(r.rooms),
                "children_not_attending": _int(r.children - r.attending),
                "attending_pct": _pct(r.attending / r.children),
                f"status_{TARGET_YEAR}": districts.status.get(r.district_id),
            }
            for i, r in enumerate(by.head(10).itertuples(), start=1)
        ],
        "ranking_rule": "Districts are ordered by places needed to reach the target; that is "
        "volume, not a full priority index (the index ranks sectors within one district).",
    }


def compare_districts(
    t: Tables, target: float, by: str = "places_needed", province: str | None = None
) -> dict[str, Any]:
    """Every district (or one province's) with the measures the screens show, sorted."""
    scope = _scope(t, province)
    needs = gap.needs(scope, target)
    track = _track(t, target)
    rows = (
        needs.groupby(["district_id", "district", "province"])
        .agg(
            children=("children_3_5", "sum"),
            attending=("attending", "sum"),
            places=("places", "sum"),
        )
        .reset_index()
    )
    rows["attending_pct"] = rows.attending / rows.children * 100
    rows["projected"] = rows.district_id.map(track.projected) * 100
    rows["status"] = rows.district_id.map(track.status)
    keys = {
        "places_needed": ("places", False),
        "attending_pct": ("attending_pct", True),
        "projected_2028_29_pct": ("projected", True),
        "children_not_attending": ("not_attending", False),
    }
    rows["not_attending"] = rows.children - rows.attending
    column, ascending = keys.get(by, keys["places_needed"])
    rows = rows.sort_values(column, ascending=ascending)
    return {
        "status": _status(scope),
        "sorted_by": by if by in keys else "places_needed",
        "target_attendance_pct": _pct(target, 0),
        "districts": [
            {
                "district": r.district,
                "province": r.province,
                "places_needed": int(r.places),
                "children_not_attending": _int(r.not_attending),
                "attending_pct": round(r.attending_pct, 1),
                f"projected_{TARGET_YEAR}_pct": round(r.projected, 1)
                if r.projected == r.projected
                else None,
                f"status_{TARGET_YEAR}": r.status,
            }
            for r in rows.head(MAX_LIST).itertuples()
        ],
    }


def district(
    t: Tables,
    district_id: str,
    target: float,
    preset: str = "Balanced",
    sectors: bool = True,
) -> dict[str, Any]:
    """One district: needs, the 2028/29 trend, and (if allowed) its sector priority ranking."""
    frame = t.sectors[t.sectors.district_id == district_id]
    if frame.empty:
        raise NotFound(f"No data for district {district_id}.")
    name = t.districts[district_id]
    status = _status(frame)
    needs = gap.needs(frame, target)
    children = needs.children_3_5.sum()
    track = _track(t, target).loc[district_id]
    rows = t.forecast[(t.forecast.geo_id == district_id)]
    observed = rows[rows.kind == "observed"].set_index("year")
    projected = rows[rows.kind == "projected"].set_index("year")
    per_year = forecast.places_per_year(
        float(observed.loc[YEARBOOK_YEARS[-1], "pupils"]),
        float(projected.children.loc[TARGET_YEAR]),
        target,
        len(PROJECTION_YEARS),
    )
    out: dict[str, Any] = {
        "district": name,
        "province": frame.province.iat[0],
        "target_attendance_pct": _pct(target, 0),
        "estimate_2026": {
            "status": status,
            "children_3_5": _int(children),
            "children_3_5_range": [_int(needs.low.sum()), _int(needs.high.sum())],
            "attending_pre_primary_pct": _pct(needs.attending.sum() / children),
            "places_needed": _int(needs.places.sum()),
            "rooms_at_30_children": _int(needs.rooms.sum()),
            "caregivers_range": [
                _int(needs.caregivers_low.sum()),
                _int(needs.caregivers_high.sum()),
            ],
            "poverty_rate_pct": _pct(frame.poverty.iloc[0]),
            "poverty_level": frame.poverty_level.iloc[0],
            "poverty_status": frame.poverty_status.iloc[0],
        },
        "trend": {
            "status": _forecast_status(t, district_id),
            "measure": "gross rate: MINEDUC pre-primary pupils per child aged 3-5",
            **_trend(track),
            f"places_a_year_still_needed_{PROJECTION_YEARS[0]}_{TARGET_YEAR}": _int(per_year),
            f"nst2_milestone_{MILESTONE_YEAR}_pct": _pct(TARGET_2027.value),
        },
        "bottlenecks": t.diagnosis[t.diagnosis.district_id == district_id]
        .bottleneck.value_counts()
        .to_dict(),
    }
    if district_id in t.plans:
        out["action_plan"] = t.plans[district_id]
    if not sectors:
        out["sectors"] = "Sector detail is shown to this district's planner and to national "
        "analysts only."
        return out
    weights = dict(zip(COMPONENTS, PRESETS.get(preset, PRESETS["Balanced"]), strict=True))
    result, used = ranked(frame, target, weights)
    diag = t.diagnosis.set_index("geo_id")
    rank_status = (
        SIMULATED if SIMULATED in (status, *frame.peer_status.dropna().unique()) else status
    )
    out["priority"] = {
        "status": rank_status,
        "more_than_1km_status": distance_status(frame),
        "main_bottleneck_status": _status(t.diagnosis[t.diagnosis.district_id == district_id]),
        "preset": preset if preset in PRESETS else "Balanced",
        "weights_used": {COMPONENT_LABELS[c]: round(w, 2) for c, w in used.items()},
        "how": "Weighted percentile ranks within the district (volume, equity, peer gap, "
        f"poverty). Stability: share of {STABILITY_DRAWS} random weightings in which the "
        "sector stays in the top 3.",
        "sectors": [
            {
                "rank": int(r.rank),
                "sector": r.name,
                "places_needed": int(r.places),
                "children_not_attending": _int(r.children_3_5 - r.attending),
                "attending_pct": _pct(r.attendance_rate),
                "more_than_1km_pct": _pct(r.far_share, 0),
                "main_bottleneck": diag.bottleneck.get(r.geo_id),
                "top3_stability": stability_label(r.stability),
                "top3_stability_pct": _pct(r.stability, 0),
            }
            for r in result.itertuples()
        ],
    }
    return out


def sector(t: Tables, geo_id: str, target: float) -> dict[str, Any]:
    """One sector, as on the Sector diagnosis screen."""
    rows = t.diagnosis.set_index("geo_id")
    if geo_id not in rows.index:
        raise NotFound(f"No diagnosis for sector {geo_id}.")
    r = rows.loc[geo_id]
    places = gap.places(target, r.children_3_5, r.attending)

    def score(v: Any) -> float | None:
        return None if v is None or v != v else round(float(v), 2)

    drivers = []
    if not bool(r.fallback) and isinstance(r.drivers, list):
        drivers = [
            {"driver": d["label"], "points_vs_average_sector": round(d["contribution_pp"], 1)}
            for d in r.drivers
        ]
    return {
        "sector": r["name"],
        "district": r.district,
        "status": SIMULATED if r.status == SIMULATED else "model estimate",
        "status_note": "status is the diagnosis's (its rules read every factor); "
        "estimate_status covers the children and attendance figures",
        "estimate_status": r.estimate_status,
        "peer_benchmark_status": r.peer_status,
        "simulated_indicators": [LABELS.get(k, k) for k in r.simulated_inputs],
        "children_3_5_2026": _int(r.children_3_5),
        "children_3_5_range": [_int(r.children_low), _int(r.children_high)],
        "attending_2026_pct": _pct(r.attendance_rate),
        "attending_census_2022_pct": _pct(r.attendance_2022),
        "target_attendance_pct": _pct(target, 0),
        "places_short": int(places),
        "main_bottleneck": r.bottleneck,
        "suggested_action": r.intervention,
        "reasons": list(r.reasons) if isinstance(r.reasons, list | tuple) else r.reasons,
        "factor_scores": {
            "note": "National percentile, 1 = worst; 0.75 or more is the worst quarter. "
            "Capacity and wellbeing are district context applied to every sector.",
            "access": score(r.access),
            "capacity": score(r.capacity),
            "wellbeing": score(r.wellbeing),
            "home_environment": score(r.home),
            "poverty": score(r.poverty_score),
        },
        "peer_benchmark": {
            "observed_census_2022_pct": _pct(r.observed),
            "expected_pct": _pct(r.expected),
            "expected_80pct_interval_pct": [_pct(r.low), _pct(r.high)],
            "benchmark": "district average (no model beat it)"
            if bool(r.fallback)
            else "peer model",
            "top_drivers": drivers,
            "drivers_note": "associated with, not caused by",
        },
        "indicators": {
            "children_more_than_1km_pct": _pct(r.far_share, 0),
            "pupils_per_teacher_district": _int(r.pupils_per_teacher),
            "qualified_teachers_district_pct": _pct(r.qualified_share, 0),
            "stunting_u5_district_pct": _pct(r.stunting, 0),
            "improved_water_pct": _pct(r.water_share, 0),
            "improved_sanitation_pct": _pct(r.sanitation_share, 0),
            "poverty_rate_pct": _pct(r.poverty, 0),
            "poverty_level": r.poverty_level,
        },
    }


def targets() -> dict[str, Any]:
    return {
        f"nst2_{TARGET_YEAR}_pct": _pct(TARGET_2029.value, 0),
        f"nst2_milestone_{MILESTONE_YEAR}_pct": _pct(TARGET_2027.value),
        "citation": TARGET_2029.citation,
    }
