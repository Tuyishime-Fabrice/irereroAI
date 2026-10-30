"""Are we on track for 65% pre-primary enrolment by 2028/29?

Rate = MINEDUC pre-primary pupils / children aged 3 to 5 (NISR projection x census 3-5
share), per district and nationally, 2020/21 to 2024/25. A linear trend is fitted and
projected to 2026/27 (NST2 milestone 54.6%) and 2028/29 (target 65%) with an 80% prediction
interval. The back-test fits 2020/21 to 2023/24 and predicts 2024/25.

    on track   projected 2028/29 rate at or above the target
    at risk    below, but the interval reaches the target
    off track  even the top of the interval is below the target

Pupils include over-age children, so the rate is a gross rate; it uses MINEDUC counts only and
is never added to census or NCDA figures.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from irerero.config import (
    CHILDREN_PER_ROOM,
    MODEL,
    OBSERVED,
    PROJECTION_YEARS,
    SIMULATED,
    TARGET_2029,
    TARGET_YEAR,
    YEARBOOK_YEARS,
)
from irerero.pipeline.inputs import Inputs
from irerero.plan.estimate import children_by_district, school_year_to_year

COVERAGE = 0.80
NATIONAL = "RW"


def start(school_year: str) -> int:
    return int(school_year[:4])


@dataclass
class Trend:
    slope: float
    intercept: float
    sigma: float
    n: int
    x_mean: float
    sxx: float

    def predict(self, x: float, coverage: float = COVERAGE) -> tuple[float, float, float]:
        centre = self.intercept + self.slope * x
        if self.n <= 2:
            return centre, centre, centre
        t = stats.t.ppf(0.5 + coverage / 2, self.n - 2)
        se = self.sigma * np.sqrt(1 + 1 / self.n + (x - self.x_mean) ** 2 / self.sxx)
        return centre, centre - t * se, centre + t * se


def fit(x: np.ndarray, y: np.ndarray) -> Trend:
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (intercept + slope * x)
    dof = max(len(x) - 2, 1)
    return Trend(
        slope=float(slope),
        intercept=float(intercept),
        sigma=float(np.sqrt(np.sum(residual**2) / dof)),
        n=len(x),
        x_mean=float(x.mean()),
        sxx=float(np.sum((x - x.mean()) ** 2)),
    )


def series(inputs: Inputs) -> pd.DataFrame:
    """geo_id, school_year, pupils, children, rate for every district and the country."""
    book = inputs.yearbook.frame[["geo_id", "school_year", "pupils"]].copy()
    book["pupils"] = book.pupils.astype(float)
    years = {sy: school_year_to_year(sy) for sy in YEARBOOK_YEARS}
    kids = {sy: children_by_district(inputs, year).children_3_5 for sy, year in years.items()}
    book["children"] = [kids[sy][g] for g, sy in zip(book.geo_id, book.school_year, strict=True)]
    national = book.groupby("school_year", as_index=False)[["pupils", "children"]].sum()
    national["geo_id"] = NATIONAL
    out = pd.concat([book, national], ignore_index=True)
    out["rate"] = out.pupils / out.children
    return out


def children_in(inputs: Inputs, school_year: str) -> pd.Series:
    kids = children_by_district(inputs, school_year_to_year(school_year)).children_3_5
    return pd.concat([kids, pd.Series({NATIONAL: kids.sum()})])


def status_for(central: float, high: float, target: float = TARGET_2029.value) -> str:
    if central >= target:
        return "on track"
    if high >= target:
        return "at risk"
    return "off track"


def forecast(inputs: Inputs) -> pd.DataFrame:
    data = series(inputs)
    status = SIMULATED if not (inputs.yearbook.real and inputs.projections.real) else None
    kids = {sy: children_in(inputs, sy) for sy in PROJECTION_YEARS}
    rows = []
    last = YEARBOOK_YEARS[-1]
    for geo_id, group in data.groupby("geo_id"):
        group = group.sort_values("school_year")
        x = group.school_year.map(start).to_numpy(float)
        y = group.rate.to_numpy(float)
        for r in group.itertuples():
            rows.append(
                (geo_id, r.school_year, "observed", r.rate, None, None, r.children, r.pupils,
                 status or OBSERVED)
            )  # fmt: skip
        trend = fit(x, y)
        for sy in PROJECTION_YEARS:
            c, lo, hi = trend.predict(start(sy))
            rows.append(
                (geo_id, sy, "projected", c, lo, hi, kids[sy][geo_id], None, status or MODEL)
            )
        back = fit(x[:-1], y[:-1])
        c, lo, hi = back.predict(start(last))
        rows.append((geo_id, last, "backtest", c, lo, hi, None, None, status or MODEL))
    out = pd.DataFrame(
        rows,
        columns=["geo_id", "year", "kind", "value", "low", "high", "children", "pupils", "status"],
    )
    for column in ("value", "low", "high"):
        out[column] = out[column].astype(float).clip(0, 1)
    return out


def summary(forecast_rows: pd.DataFrame, target: float = TARGET_2029.value) -> pd.DataFrame:
    """Per geo_id: latest observed, 2028/29 projection, status, back-test error."""
    f = forecast_rows
    last = YEARBOOK_YEARS[-1]
    observed = f[(f.kind == "observed") & (f.year == last)].set_index("geo_id").value
    proj = f[(f.kind == "projected") & (f.year == TARGET_YEAR)].set_index("geo_id")
    back = f[f.kind == "backtest"].set_index("geo_id")
    out = pd.DataFrame(
        {
            "latest": observed,
            "projected": proj.value,
            "low": proj.low,
            "high": proj.high,
            "backtest_error_pp": (back.value - observed) * 100,
            "backtest_inside": (observed >= back.low) & (observed <= back.high),
        }
    )
    out["status"] = [status_for(c, h, target) for c, h in zip(out.projected, out.high, strict=True)]
    return out


def places_per_year(
    latest_pupils: float, children_target_year: float, target: float, years_left: int
) -> float:
    """Extra pre-primary places a year needed to reach `target` by the target year."""
    return max(0.0, target * children_target_year - latest_pupils) / max(years_left, 1)


def whatif(
    projected: pd.Series,
    children: pd.Series,
    rooms_per_year: float,
    first_year: str,
    max_places: float | None = None,
) -> pd.Series:
    """Projected rate per school year with `rooms_per_year` extra rooms added each year from
    `first_year`, every place filled. `projected` and `children` are indexed by school year.
    With `max_places` (what the chosen sectors need), places beyond it stay empty and add
    nothing."""
    years = list(projected.index)
    added = pd.Series(
        [max(0, years.index(sy) - years.index(first_year) + 1) for sy in years], index=years
    )
    extra = added * rooms_per_year * CHILDREN_PER_ROOM.value
    if max_places is not None:
        extra = extra.clip(upper=max(max_places, 0))
    return (projected + extra / children).clip(upper=1.0)
