"""Screen 1. National overview: where the formal pre-primary gap is, by district and sector."""

import pandas as pd
import streamlit as st

from irerero.config import STATUS_COLOURS, TARGET_2029, TARGET_YEAR
from irerero.plan import gap
from irerero.plan.frame import any_simulated
from irerero.track import forecast
from irerero.ui import data, maps, theme

sectors = data.sectors()
simulated = any_simulated(sectors)
theme.header(
    "National overview",
    "Children aged 3 to 5 in 2026 and the pre-primary places needed to reach the target.",
    simulated=simulated,
)

target = TARGET_2029.value
needs = gap.needs(sectors, target)
status = "simulated" if simulated else "model estimate"
source = "IrereroAI 2026 estimate"

c1, c2, c3, c4 = st.columns(4)
with c1:
    theme.card(
        "Children aged 3 to 5 (2026)",
        theme.fmt_int(needs.children_3_5.sum()),
        source,
        "2026",
        status,
        f"range {theme.fmt_int(needs.low.sum())} to {theme.fmt_int(needs.high.sum())}",
    )
with c2:
    rate = needs.attending.sum() / needs.children_3_5.sum()
    theme.card("Attending pre-primary (2026)", theme.fmt_pct(rate, 1), source, "2026", status)
with c3:
    theme.card(
        f"Places needed for {theme.fmt_pct(target)}",
        theme.fmt_int(needs.places.sum()),
        source,
        "2026",
        status,
        f"{theme.fmt_int(needs.rooms.sum())} rooms at 30 children each",
    )
with c4:
    far = (needs.far_share * needs.children_3_5).sum() / needs.children_3_5.sum()
    theme.card(
        "Children more than 1 km from a school",
        theme.fmt_pct(far),
        "IrereroAI distance layer",
        "2026",
        status,
        needs.distance_method.mode().iat[0] if len(needs) else None,
    )

st.subheader("Where the gap is")
view = st.radio(
    "Map",
    [
        f"{TARGET_YEAR} status, by district",
        "Places needed, by sector",
        "Attendance rate, by district",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
if view.startswith(TARGET_YEAR):
    track = forecast.summary(data.table("forecast"), target).drop(index=forecast.NATIONAL)
    maps.choropleth(
        data.geojson("district"),
        track.projected.to_dict(),
        f"Projected {TARGET_YEAR} enrolment",
        lambda v: theme.fmt_pct(v),
        tooltip={
            g: f"{r.status} · 80% range {theme.fmt_pct(r.low)}–{theme.fmt_pct(r.high)} · {status}"
            for g, r in track.iterrows()
        },
        colours={g: STATUS_COLOURS[s] for g, s in track.status.items()},
        key="national-status",
    )
    counts = track.status.value_counts()
    st.markdown(
        " ".join(
            theme.chip(f"{k}: {counts.get(k, 0)} districts", c) for k, c in STATUS_COLOURS.items()
        )
        + f' <span class="ir-note">Trend of MINEDUC enrolment projected to {TARGET_YEAR} '
        f"against {theme.fmt_pct(target)}; see Plan builder for the method.</span>",
        unsafe_allow_html=True,
    )
elif view.startswith("Places"):
    maps.choropleth(
        data.geojson("sector"),
        dict(zip(needs.geo_id, needs.places, strict=True)),
        f"Places needed for {theme.fmt_pct(target)}",
        theme.fmt_int,
        tooltip={
            r.geo_id: f"{r.district} · {theme.fmt_pct(r.attendance_rate)} attending · {status}"
            for r in needs.itertuples()
        },
        key="national-sectors",
    )
else:
    by_district = needs.groupby("district_id").agg(
        children=("children_3_5", "sum"), attending=("attending", "sum")
    )
    rate = by_district.attending / by_district.children
    maps.choropleth(
        data.geojson("district"),
        rate.to_dict(),
        "Attending pre-primary (2026)",
        lambda v: theme.fmt_pct(v),
        tooltip={k: status for k in rate.index},
        key="national-districts",
    )

st.subheader("Districts")
table = (
    needs.groupby(["district_id", "district", "province"])
    .agg(
        children=("children_3_5", "sum"),
        attending=("attending", "sum"),
        places=("places", "sum"),
        rooms=("rooms", "sum"),
    )
    .reset_index()
)
table["rate"] = table.attending / table.children
table = table.sort_values("places", ascending=False)
st.dataframe(
    pd.DataFrame(
        {
            "District": table.district,
            "Province": table.province,
            "Children 3-5 (2026)": table.children.round().astype(int),
            "Attending": table.rate * 100,
            f"Places for {theme.fmt_pct(target)}": table.places,
            "Rooms": table.rooms,
            "Status": status,
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Attending": st.column_config.ProgressColumn(
            "Attending", format="%.0f%%", min_value=0, max_value=100
        ),
    },
)
theme.note(
    f"Target {theme.fmt_pct(target)}: {TARGET_2029.citation}. Rooms and places: "
    "National ECD Standards (2024). Hover a number for its source, year and status."
)
