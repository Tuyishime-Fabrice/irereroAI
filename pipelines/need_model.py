"""Replace parts of the simulated need with official values wherever their files are loaded."""

from typing import Any

from sqlalchemy import Connection, text

from irerero_engine.need import AreaNeed, LayeredNeedEstimator, Loaded
from irerero_engine.types import Range, SourceRef

SOURCE_LIMIT = 160
LOADED = text(
    """
    SELECT area_code, indicator, value, low, high, source, reference_year, origin
    FROM area_indicator
    WHERE origin <> 'simulated' AND indicator IN ('population_0_2', 'population_3_6',
        'stunting_prevalence_u5', 'mothers_childcare_barrier_share')
    """
)
UPDATE = text(
    """
    UPDATE need_estimate SET
        children_0_2_estimate = :c02e, children_0_2_low = :c02l, children_0_2_high = :c02h,
        children_3_6_estimate = :c36e, children_3_6_low = :c36l, children_3_6_high = :c36h,
        stunting_risk_estimate = :se, stunting_risk_low = :sl, stunting_risk_high = :sh,
        mothers_barrier_share_estimate = :be, mothers_barrier_share_low = :bl,
        mothers_barrier_share_high = :bh, model_version_id = :model, source = :source,
        reference_year = :year, origin = :origin
    WHERE area_code = :area
    """
)


def _range(row: Any, prefix: str) -> Range:
    return Range(
        getattr(row, f"{prefix}_estimate"),
        getattr(row, f"{prefix}_low"),
        getattr(row, f"{prefix}_high"),
    )


def _short(source: str) -> str:
    return source.split(" (")[0].split(",")[0]


def describe(need: AreaNeed) -> tuple[str, str, int]:
    """(source text, origin, reference year) for a row built from three components."""
    children, stunting, barrier = need.sources
    names = [_short(s.source) for s in need.sources]
    if len(set(names)) == 1:
        text_ = names[0]
    else:
        text_ = f"children: {names[0]}; stunting: {names[1]}; mothers' barrier: {names[2]}"
    origins = {s.origin for s in need.sources}
    origin = (
        "simulated"
        if "simulated" in origins
        else "official"
        if origins == {"official"}
        else sorted(origins - {"official"})[0]
    )
    year = max(s.reference_year for s in (children, stunting, barrier))
    return text_[:SOURCE_LIMIT], origin, year


def apply_loaded_need(conn: Connection) -> int:
    """Returns the number of areas that now use at least one official value."""
    loaded: dict[str, dict[str, Loaded]] = {}
    for row in conn.execute(LOADED):
        low = row.low if row.low is not None else row.value
        high = row.high if row.high is not None else row.value
        loaded.setdefault(row.indicator, {})[row.area_code] = Loaded(
            Range(row.value, low, high),
            SourceRef("area_indicator", row.source, row.reference_year, row.origin),
        )
    if not loaded:
        return 0
    base = {}
    for row in conn.execute(text("SELECT * FROM need_estimate")):
        source = SourceRef("need_estimate", row.source, row.reference_year, row.origin)
        base[row.area_code] = AreaNeed(
            row.area_code,
            _range(row, "children_0_2"),
            _range(row, "children_3_6"),
            _range(row, "stunting_risk"),
            _range(row, "mothers_barrier_share"),
            (source, source, source),
            row.model_version_id,
        )
    parents = dict(conn.execute(text("SELECT code, parent_code FROM admin_unit")).all())
    estimator = LayeredNeedEstimator(
        base,
        parents,
        loaded.get("population_0_2", {}),
        loaded.get("population_3_6", {}),
        loaded.get("stunting_prevalence_u5", {}),
        loaded.get("mothers_childcare_barrier_share", {}),
    )
    changed = 0
    for code, need in estimator.estimate(sorted(base)).items():
        if all(s.table == "need_estimate" for s in need.sources):
            continue
        source, origin, year = describe(need)
        conn.execute(
            UPDATE,
            {
                "area": code,
                "c02e": round(need.children_0_2.estimate),
                "c02l": round(need.children_0_2.low),
                "c02h": round(need.children_0_2.high),
                "c36e": round(need.children_3_6.estimate),
                "c36l": round(need.children_3_6.low),
                "c36h": round(need.children_3_6.high),
                "se": need.stunting_risk.estimate,
                "sl": need.stunting_risk.low,
                "sh": need.stunting_risk.high,
                "be": need.mothers_barrier_share.estimate,
                "bl": need.mothers_barrier_share.low,
                "bh": need.mothers_barrier_share.high,
                "model": need.model_version,
                "source": source,
                "year": year,
                "origin": origin,
            },
        )
        changed += 1
    return changed
