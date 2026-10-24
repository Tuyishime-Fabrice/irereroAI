"""Charts shared by several screens, in the house style (Altair theme set in theme.setup)."""

from html import escape

import altair as alt
import pandas as pd

from irerero.config import (
    MILESTONE_YEAR,
    PROJECTION_YEARS,
    TARGET_2027,
    TARGET_YEAR,
    YEARBOOK_YEARS,
)
from irerero.ui.theme import GOLD_700, SERIES, SERIES_MUTED

ORDER = list(YEARBOOK_YEARS) + list(PROJECTION_YEARS)


def trend(
    observed: pd.DataFrame,
    projected: pd.DataFrame,
    target: float,
    with_plan: pd.Series | None = None,
    height: int = 300,
) -> alt.LayerChart:
    """Enrolment rate: observed years, the projected trend with its 80% band, an optional
    what-if line, and the NST2 milestone and target as labelled markers. `observed` and
    `projected` are indexed by school year with value (and low/high for projected)."""
    last_year = observed.index[-1]
    last = float(observed.value.iloc[-1])
    rows = [{"year": y, "value": r.value, "series": "Observed"} for y, r in observed.iterrows()]
    rows += [{"year": last_year, "value": last, "series": "Trend"}]
    rows += [{"year": y, "value": r.value, "series": "Trend"} for y, r in projected.iterrows()]
    domain, colours = ["Observed", "Trend"], [SERIES[0], SERIES_MUTED]
    if with_plan is not None:
        rows += [{"year": last_year, "value": last, "series": "With added rooms"}]
        rows += [
            {"year": y, "value": v, "series": "With added rooms"} for y, v in with_plan.items()
        ]
        domain.append("With added rooms")
        colours.append(SERIES[1])
    frame = pd.DataFrame(rows)
    band = pd.DataFrame(
        [{"year": last_year, "low": last, "high": last}]
        + [{"year": y, "low": r.low, "high": r.high} for y, r in projected.iterrows()]
    )
    x = alt.X("year:N", sort=ORDER, title=None, axis=alt.Axis(labelAngle=0))
    y_axis = alt.Axis(format="%", tickCount=5)
    area = (
        alt.Chart(band)
        .mark_area(opacity=0.18, color=SERIES[0])
        .encode(x=x, y=alt.Y("low:Q", axis=y_axis, title=None), y2="high:Q",
                tooltip=[alt.Tooltip("year:N"), alt.Tooltip("low:Q", format=".1%", title="80% low"),
                         alt.Tooltip("high:Q", format=".1%", title="80% high")])
    )  # fmt: skip
    lines = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=45, filled=True))
        .encode(
            x=x,
            y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1]), axis=y_axis, title=None),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(domain=domain, range=colours),
                legend=None,  # trend_legend() draws it in HTML so it wraps on a phone
            ),
            strokeDash=alt.condition(
                alt.datum.series == "Trend", alt.value([5, 4]), alt.value([1, 0])
            ),
            tooltip=["series", "year", alt.Tooltip("value:Q", format=".1%", title="rate")],
        )
    )
    targets = pd.DataFrame(
        [
            {"year": MILESTONE_YEAR, "value": TARGET_2027.value, "label": "NST2 milestone 54.6%"},
            {"year": TARGET_YEAR, "value": target, "label": f"Target {target:.0%}"},
        ]
    )
    marks = (
        alt.Chart(targets)
        .mark_point(shape="diamond", size=110, filled=True, color=GOLD_700, stroke="white",
                    strokeWidth=2)
        .encode(x=x, y="value:Q", tooltip=["label"])
    )  # fmt: skip
    labels = (
        alt.Chart(targets)
        .mark_text(dx=-6, dy=-12, align="right", color=GOLD_700, fontWeight=600, fontSize=11)
        .encode(x=x, y="value:Q", text="label")
    )
    return (area + lines + marks + labels).properties(height=height)


def trend_legend(with_plan: bool = False) -> str:
    """HTML legend for trend(): line style and colour, and the words, for every mark."""
    items = [
        ("", SERIES[0], "Observed (MINEDUC)"),
        ("dash", SERIES_MUTED, "Trend, with 80% range"),
    ]
    if with_plan:
        items.append(("", SERIES[1], "With added rooms"))
    items.append(("diamond", GOLD_700, "NST2 milestone and target"))
    spans = "".join(
        f'<span><i class="{cls}" style="border-color:{colour}'
        + (f";background:{colour}" if cls == "diamond" else "")
        + f'"></i>{escape(text)}</span>'
        for cls, colour, text in items
    )
    return f'<div class="ir-legend" role="list" aria-label="Chart legend">{spans}</div>'
