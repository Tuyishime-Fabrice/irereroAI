"""Screen 2. District priorities (PLAN): which sectors need pre-primary places first."""

import pandas as pd
import streamlit as st

from irerero.config import (
    COMPONENT_LABELS,
    COMPONENTS,
    GREEN,
    MUTED,
    PRESETS,
    STABILITY_DRAWS,
    TARGET_2029,
)
from irerero.plan.frame import any_simulated, ranked
from irerero.plan.priority import stability_label
from irerero.ui import data, maps, theme
from irerero.ui.roles import ANALYST, current

user = current()
all_sectors = data.sectors()
districts = data.districts()

if user.role == ANALYST:
    district_id = st.selectbox("District", list(districts), format_func=districts.get)
else:
    district_id = user.district_id
frame = all_sectors[all_sectors.district_id == district_id]
simulated = any_simulated(frame)
theme.header(
    f"District priorities · {districts[district_id]}",
    "Which sectors need pre-primary places first, and how sure we can be of the order.",
    simulated=simulated,
)

with st.container(border=True):
    left, right = st.columns([1, 1])
    with left:
        target_pct = st.slider(
            "Target attendance (%)",
            30,
            90,
            round(data.target() * 100),
            help=f"Default {theme.fmt_pct(TARGET_2029.value)}: {TARGET_2029.citation}",
        )
        st.session_state["target_pct"] = target_pct  # kept across screens
        target = target_pct / 100
        preset = st.radio(
            "Priority preset", [*PRESETS, "Custom"], horizontal=True, index=2, key="preset"
        )
    with right:
        base = PRESETS.get(preset, PRESETS["Balanced"])
        weights = {}
        grid = st.columns(2)
        for i, (component, default) in enumerate(zip(COMPONENTS, base, strict=True)):
            weights[component] = grid[i % 2].slider(
                COMPONENT_LABELS[component],
                0.0,
                1.0,
                float(default),
                0.05,
                disabled=preset != "Custom",
                key=f"w-{component}-{preset}",
            )

result, used = ranked(frame, target, weights)
if "peer_gap" not in used:
    st.info(
        "The peer-gap component is not available yet (the DIAGNOSE peer model has not run), so "
        "its weight is shared among the other components."
    )

status = "simulated" if simulated else "model estimate"
c1, c2, c3, c4 = st.columns(4)
with c1:
    theme.card(
        "Children aged 3 to 5 (2026)",
        theme.fmt_int(result.children_3_5.sum()),
        "IrereroAI 2026 estimate",
        "2026",
        status,
        f"range {theme.fmt_int(result.low.sum())} to {theme.fmt_int(result.high.sum())}",
    )
with c2:
    theme.card(
        f"Places to reach {theme.fmt_pct(target)}",
        theme.fmt_int(result.places.sum()),
        "places = max(0, ceil(t·P) − A)",
        "2026",
        status,
    )
with c3:
    theme.card(
        "Rooms (30 children each)",
        theme.fmt_int(result.rooms.sum()),
        "National ECD Standards 2024",
        "2024",
        status,
    )
with c4:
    theme.card(
        "Caregivers (1:30 to 1:15)",
        f"{theme.fmt_int(result.caregivers_low.sum())}–"
        f"{theme.fmt_int(result.caregivers_high.sum())}",
        "National ECD Standards 2024",
        "2024",
        status,
    )

table_col, map_col = st.columns([3, 2])
with table_col:
    st.subheader("Ranked sectors")
    show = pd.DataFrame(
        {
            "Rank": result["rank"],
            "Sector": result.name,
            "Children 3-5": result.children_3_5.round().astype(int),
            "Range": [
                f"{theme.fmt_int(lo)}–{theme.fmt_int(hi)}"
                for lo, hi in zip(result.low, result.high, strict=True)
            ],
            "Attending": result.attendance_rate * 100,
            "Places": result.places,
            "Rooms": result.rooms,
            "Caregivers": [
                f"{lo}–{hi}"
                for lo, hi in zip(result.caregivers_low, result.caregivers_high, strict=True)
            ],
            "> 1 km": result.far_share * 100,
            "Score": result.score,
            "Top-3 stability": [f"{stability_label(s)} ({s:.0%})" for s in result.stability],
            "Status": status,
        }
    )
    st.dataframe(
        show,
        hide_index=True,
        use_container_width=True,
        height=min(42 + 35 * len(show), 520),
        column_config={
            "Attending": st.column_config.NumberColumn(format="%.0f%%"),
            "> 1 km": st.column_config.NumberColumn(
                format="%.0f%%", help="Share of children aged 3 to 5 more than 1 km from a school"
            ),
            "Score": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
            "Top-3 stability": st.column_config.TextColumn(
                help=f"Share of {STABILITY_DRAWS} random weightings around the chosen weights "
                "in which the sector stays in the top 3"
            ),
        },
    )
with map_col:
    st.subheader("Map")
    geo = data.geojson("sector")
    ids = set(result.geo_id)
    maps.choropleth(
        geo,
        dict(zip(result.geo_id, result.score, strict=True)),
        "Priority score",
        lambda v: f"{v:.2f}",
        tooltip={
            r.geo_id: f"Rank {r.rank} · {theme.fmt_int(r.places)} places · {status}"
            for r in result.itertuples()
        },
        view=maps.view_for(geo, ids),
        height=420,
        key="priority-map",
    )

st.subheader("Why this order")
weights_text = " · ".join(f"{COMPONENT_LABELS[c]} {w:.0%}" for c, w in used.items())
st.markdown(f"Weights used: {weights_text}")
top = result.head(3)
for r in top.itertuples():
    parts = [
        f"{COMPONENT_LABELS[c]}: {theme.ordinal(round(getattr(r, f'pct_{c}') * 100))} percentile"
        for c in used
    ]
    colour = GREEN if r.stability >= 0.8 else MUTED
    st.markdown(
        f"**{r.rank}. {r.name}** {theme.chip(stability_label(r.stability), colour)}  \n"
        + "; ".join(parts),
        unsafe_allow_html=True,
    )
methods = result.distance_method.iloc[0] if len(result) else ""
theme.note(
    f"Distance: {methods}. Ranks are within {districts[district_id]}: a percentile says how a "
    "sector compares with the other sectors of the district, not an absolute need. Estimates "
    "are ranges; the order of sectors close in score can change."
)
