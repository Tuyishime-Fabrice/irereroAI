"""The planning table: one row per sector with its estimate, names, poverty and peer gap, from
the database. Pure pandas, so the app and the tests use the same code."""

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import Engine

from irerero.config import MODEL, PROVISIONAL, SIMULATED
from irerero.db.store import read
from irerero.plan import gap, priority


def latest(observations: pd.DataFrame, indicator: str) -> pd.DataFrame:
    """The most recent value of an indicator per geo_id, with its source, period and status."""
    rows = observations[observations.indicator_id == indicator]
    rows = rows.sort_values("reference_period").groupby("geo_id").tail(1)
    return rows.set_index("geo_id")[["value", "source_id", "reference_period", "status"]]


def sectors(eng: Engine) -> pd.DataFrame:
    units = read(eng, "geo_unit")
    est = read(eng, "estimate_2026")
    obs = read(eng, "observation")
    out = est.merge(
        units[["geo_id", "name", "parent_id", "district", "province"]], on="geo_id", how="left"
    ).rename(columns={"parent_id": "district_id"})

    poverty = latest(obs, "poverty_rate")
    sector_poverty = out.geo_id.map(poverty.value)
    district_poverty = out.district_id.map(poverty.value)
    out["poverty"] = sector_poverty.fillna(district_poverty)
    out["poverty_level"] = sector_poverty.notna().map({True: "sector", False: "district"})
    out["poverty_status"] = out.geo_id.map(poverty.status).fillna(
        out.district_id.map(poverty.status)
    )

    model = read(eng, "model_output")
    if len(model):
        model = model.set_index("geo_id")
        out["expected"] = out.geo_id.map(model.expected)
        out["expected_low"] = out.geo_id.map(model.low)
        out["expected_high"] = out.geo_id.map(model.high)
        out["peer_status"] = out.geo_id.map(model.status)
    else:
        out["expected"] = out["expected_low"] = out["expected_high"] = float("nan")
        out["peer_status"] = None
    return out


def components(frame: pd.DataFrame) -> pd.DataFrame:
    """Raw values of the four priority components, indexed by geo_id. `frame` needs places."""
    peer = (frame.expected - frame.attendance_rate).clip(lower=0)
    return pd.DataFrame(
        {
            "volume": frame.places.astype(float),
            "equity": 1 - frame.attendance_rate,
            "peer_gap": peer,
            "poverty": frame.poverty,
        }
    ).set_axis(frame.geo_id)


def ranked(
    frame: pd.DataFrame,
    target: float,
    weights: Mapping[str, float],
    stability: bool = True,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Needs and priority for the sectors in `frame`, best first, and the weights actually
    used (components without data drop out and their weight is shared)."""
    out = gap.needs(frame, target)
    comps = components(out)
    pct = priority.percentiles(comps)
    used = priority.normalise(weights, list(pct.columns))
    out = out.set_index("geo_id")
    out["score"] = priority.score(pct, used)
    out["rank"] = priority.rank(pct, used)
    for c in pct.columns:
        out[f"pct_{c}"] = pct[c]
    if stability:
        out["stability"] = priority.stability(pct, used)
    return out.sort_values("rank").reset_index(), used


def status_of(frame: pd.DataFrame) -> str:
    """One status for a table on screen: simulated when any of its rows is."""
    if frame.empty or "status" not in frame:
        return MODEL
    return SIMULATED if (frame.status == SIMULATED).any() else str(frame.status.mode().iat[0])


def distance_status(frame: pd.DataFrame) -> str:
    """The distance layer is simulated while the school points are, even on a real estimate,
    and provisional while they are a partial list."""
    method = frame.distance_method.astype(str)
    if method.str.contains("simulated").any():
        return SIMULATED
    if method.str.contains("provisional").any():
        return PROVISIONAL
    return status_of(frame)
