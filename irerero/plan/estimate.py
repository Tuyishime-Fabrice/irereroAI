"""2026 estimate of children aged 3 to 5 per sector, and of those attending pre-primary.

1. District total for 2026: NISR projected children aged 3 to 5 when the single-age tables
   are loaded; otherwise projected population x the district's census 3-5 share.
2. Split across sectors: WorldPop under-5 per sector x the district's census ratio of 3-5 to
   0-4 children; while WorldPop is missing, each sector's share of the district's census 3-5
   count.
3. Range: projection range (or PROJECTION_REL_ERROR) combined with the disagreement between
   WorldPop and census sector shares (or SHARE_DRIFT_REL).
4. Attending: the sector's 2022 census attendance rate, moved by the district's change in
   MINEDUC pupils per child from 2021/22 (census year) to the latest yearbook. A real census is
   never moved by a simulated yearbook: until the yearbook series is real, the rate stays at
   its 2022 value and the method says so.

Census, MINEDUC and NCDA counts are never added together: MINEDUC only moves the census rate.
"""

import numpy as np
import pandas as pd

from irerero.config import (
    ESTIMATE_YEAR,
    MAX_ATTENDANCE,
    MODEL,
    PROJECTION_REL_ERROR,
    SHARE_DRIFT_REL,
    SIMULATED,
    YEARBOOK_YEARS,
)
from irerero.pipeline.inputs import Inputs

CENSUS_YEAR = 2022
CENSUS_SCHOOL_YEAR = "2021/22"


def projected(inputs: Inputs, year: int, column: str = "population") -> pd.DataFrame:
    """A projected district `column` in `year`, with low/high from the population variants.
    Years before the series starts are extrapolated back at the growth rate of its first two
    years."""
    proj = inputs.projections.frame
    wide = proj.pivot_table(index="geo_id", columns="year", values=column, aggfunc="sum")
    if year not in wide.columns:
        first, second = sorted(wide.columns)[:2]
        if year > first:
            raise ValueError(f"no projection for {year}")
        values = wide[first] * (wide[first] / wide[second]) ** (first - year)
        return pd.DataFrame({"population": values, "low": values, "high": values})
    rows = proj[proj.year == year].set_index("geo_id")
    value = rows[column].astype(float)
    population = rows.population.astype(float)
    # an empty variant column (no low/high published) is all NA
    low = (pd.to_numeric(rows.population_low, errors="coerce") / population * value).fillna(value)
    high = (pd.to_numeric(rows.population_high, errors="coerce") / population * value).fillna(value)
    return pd.DataFrame({"population": value, "low": low, "high": high})


def projects_children(inputs: Inputs) -> bool:
    """The projections carry children aged 3 to 5 directly (the single-age tables)."""
    frame = inputs.projections.frame
    return "children_3_5" in frame and bool(frame.children_3_5.notna().all())


def school_year_to_year(school_year: str) -> int:
    """2021/22 -> 2022: the calendar year in which the school year ends (census 2022 matches
    2021/22)."""
    return int(school_year[:4]) + 1


def children_by_district(inputs: Inputs, year: int) -> pd.DataFrame:
    """Children aged 3 to 5 per district in `year`: projected directly when the projections
    carry them, otherwise projected population x census 3-5 share."""
    if projects_children(inputs):
        return projected(inputs, year, "children_3_5").rename(
            columns={"population": "children_3_5"}
        )
    census = inputs.census_districts.frame.set_index("geo_id")
    pop = projected(inputs, year)
    if census.population.notna().all():
        share = census.children_3_5.astype(float) / census.population.astype(float)
        base = pop.mul(share, axis=0)
    else:  # no census population: grow the census count with the projection
        growth = pop.div(projected(inputs, CENSUS_YEAR).population, axis=0)
        base = growth.mul(census.children_3_5.astype(float), axis=0)
    return base.rename(columns={"population": "children_3_5"})


def attendance_trend(inputs: Inputs) -> pd.Series:
    """Per district: MINEDUC pupils per child in the latest yearbook / in 2021/22."""
    book = inputs.yearbook.frame.set_index(["geo_id", "school_year"]).pupils.astype(float)
    latest = YEARBOOK_YEARS[-1]
    latest_year = int(latest[:4]) + 1
    kids_then = children_by_district(inputs, CENSUS_YEAR).children_3_5
    kids_now = children_by_district(inputs, latest_year).children_3_5
    then = book.xs(CENSUS_SCHOOL_YEAR, level="school_year") / kids_then
    now = book.xs(latest, level="school_year") / kids_now
    return (now / then).rename("trend")


def estimate(inputs: Inputs) -> pd.DataFrame:
    sectors = inputs.census_sectors.frame.set_index("geo_id")
    districts = inputs.census_districts.frame.set_index("geo_id")
    parent = inputs.sectors.set_index("geo_id").parent_id.loc[sectors.index]
    totals = children_by_district(inputs, ESTIMATE_YEAR)

    census_share = sectors.children_3_5.astype(float) / parent.map(
        sectors.children_3_5.astype(float).groupby(parent).sum()
    )
    if inputs.under5 is not None:
        ratio = districts.children_3_5.astype(float) / districts.children_0_4.astype(float)
        raw = inputs.under5.reindex(sectors.index).astype(float) * parent.map(ratio)
        share = raw / parent.map(raw.groupby(parent).sum())
        drift = ((share - census_share).abs() / census_share).clip(upper=1.0)
        method = "WorldPop under-5 x census age ratio"
    else:
        share = census_share
        drift = pd.Series(SHARE_DRIFT_REL, index=sectors.index)
        method = "census 2022 sector share"
    method += (
        " of NISR projected children aged 3-5"
        if projects_children(inputs)
        else ", calibrated to NISR projections"
    )

    total = parent.map(totals.children_3_5)
    projection_rel = parent.map((totals.high - totals.low) / 2 / totals.children_3_5).replace(
        0, PROJECTION_REL_ERROR
    )
    rel = np.sqrt(projection_rel**2 + drift**2)
    children = share * total

    rate_2022 = sectors.children_3_5_attending.astype(float) / sectors.children_3_5.astype(float)
    # The trend applies when the yearbook is as real as the census (the demo moves simulated
    # rates by a simulated trend, to show the method).
    with_trend = inputs.yearbook.real or not inputs.census_sectors.real
    if with_trend:
        rate = (rate_2022 * parent.map(attendance_trend(inputs))).clip(upper=MAX_ATTENDANCE)
        method += "; attendance: census 2022 rate moved by the MINEDUC trend"
    else:
        rate = rate_2022.clip(upper=MAX_ATTENDANCE)
        method += (
            "; attendance: census 2022 rate, not yet moved by MINEDUC (yearbook series incomplete)"
        )

    inputs_real = (
        inputs.census_sectors.real
        and inputs.projections.real
        and (inputs.yearbook.real or not with_trend)
    )
    out = pd.DataFrame(
        {
            "geo_id": sectors.index,
            "district_id": parent.to_numpy(),
            "children_3_5": children.round().to_numpy(),
            "low": (children * (1 - rel)).round().to_numpy(),
            "high": (children * (1 + rel)).round().to_numpy(),
            "attendance_rate_2022": rate_2022.round(4).to_numpy(),
            "attendance_rate": rate.round(4).to_numpy(),
            "status": MODEL if inputs_real else SIMULATED,
            "method": method,
        }
    )
    out["attending"] = (out.children_3_5 * out.attendance_rate).round()
    return out
