"""Screen 2. District priorities (PLAN): where new pre-primary places are needed first."""

import streamlit as st

from irerero.config import (
    COMPONENT_LABELS,
    COMPONENTS,
    PRESETS,
    SIMULATED,
    STABILITY_DRAWS,
    TARGET_2029,
)
from irerero.plan.frame import distance_status, ranked, status_of
from irerero.plan.priority import stability_label
from irerero.ui import data, maps, theme
from irerero.ui.roles import ANALYST, current
from irerero.ui.theme import Col

user = current()
all_sectors = data.sectors()
districts = data.districts()
ids = list(districts)
if user.role == ANALYST:
    district_id = st.session_state.get("prio-district", ids[0])
else:
    district_id = user.district_id
frame = all_sectors[all_sectors.district_id == district_id]
province = frame.province.iat[0] if len(frame) else ""
# the ranking reads the estimate, the peer gap and poverty; the table also shows distance
# (school points) and the main bottleneck (every DIAGNOSE factor), each with its own status
status = (
    SIMULATED
    if SIMULATED in (status_of(frame), *frame.peer_status.dropna().unique())
    else status_of(frame)
)
far_status = distance_status(frame)
diag_status = status_of(data.diagnosis_now(data.target()))
simulated = SIMULATED in (status, far_status, diag_status)

theme.header(
    "District priorities",
    "Find where new pre-primary places are needed first, and how sure we can be of the order.",
    simulated=simulated,
    crumbs=["Rwanda", province, districts[district_id], "District priorities"],
    assistant="priorities",
)

# --- filters ------------------------------------------------------------------------------
with theme.panel(key="filters"):
    f1, f2, f3 = st.columns([1, 1, 1.2])
    if user.role == ANALYST:
        f1.selectbox("District", ids, format_func=districts.get, key="prio-district")
    else:
        f1.selectbox("District", [district_id], format_func=districts.get, disabled=True,
                     help="Planners see their own district.")  # fmt: skip
    preset = f2.selectbox(
        "Priority preset",
        [*PRESETS, "Custom"],
        index=2,
        key="preset",
        help="Reach most children, Equity first and Balanced set the weights; Custom unlocks them.",
    )
    target_pct = f3.slider(
        "Target attendance (%)",
        30,
        90,
        round(data.target() * 100),
        help=f"Default {theme.fmt_pct(TARGET_2029.value)}: {TARGET_2029.citation}",
    )
    st.session_state["target_pct"] = target_pct  # kept across screens
target = target_pct / 100

kpi_row = st.container()  # filled once the ranking is known
main, side = st.columns([5, 3])
weights_col, why_col = st.columns([1, 1])

# --- weights are read before the ranking above them is drawn ------------------------------
with (
    weights_col,
    theme.panel(
        "How ranking works", "Each component is a percentile among the district's sectors.", "scale"
    ),
):
    base = PRESETS.get(preset, PRESETS["Balanced"])
    weights = {}
    for component, default in zip(COMPONENTS, base, strict=True):
        weights[component] = st.slider(
            COMPONENT_LABELS[component],
            0.0,
            1.0,
            float(default),
            0.05,
            disabled=preset != "Custom",
            key=f"w-{component}-{preset}",
        )
    if preset != "Custom":
        theme.note(f"Preset '{preset}'. Choose Custom in the filters to set your own weights.")

result, used = ranked(frame, target, weights)
diag = data.diagnosis_now(target).set_index("geo_id")
result["bottleneck"] = result.geo_id.map(diag.bottleneck)
result["not_attending"] = (result.children_3_5 - result.attending).clip(lower=0)
stable = result[result.stability >= 0.8]
top3 = result.head(3)

# --- KPIs ---------------------------------------------------------------------------------
with kpi_row:
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        theme.kpi("Sectors", str(len(result)), "NISR boundaries", "2022", None,
                  f"in {districts[district_id]}", "school", "navy")  # fmt: skip
    with k2:
        theme.kpi("Stable top-3 sectors", str(len(stable)), "IrereroAI rank stability", "2026",
                  status, f"in the top 3 in ≥80% of {STABILITY_DRAWS} weightings", "target", "teal")  # fmt: skip
    with k3:
        theme.kpi("Places in top 3", theme.fmt_int(top3.places.sum()), "places = max(0, ⌈t·P⌉ − A)",
                  "2026", status, f"to reach {theme.fmt_pct(target)}", "users", "blue")  # fmt: skip
    with k4:
        theme.kpi(
            "All places needed",
            theme.fmt_int(result.places.sum()),
            "National ECD Standards 2024",
            "2026",
            status,
            f"{theme.fmt_int(result.rooms.sum())} rooms · {theme.fmt_int(result.caregivers_low.sum())}"
            f"–{theme.fmt_int(result.caregivers_high.sum())} caregivers",
            "rooms",
            "gold",
        )

# --- ranking table ------------------------------------------------------------------------
with (
    main,
    theme.panel(
        "Sector ranking and needs",
        f"Children aged 3–5 (2026 estimate) · target {theme.fmt_pct(target)} · status: {status}",
        "chart",
    ),
):
    st.markdown(
        theme.table(
            result.to_dict(orient="records"),
            [
                Col("rank", "Rank", num=True),
                Col("name", "Sector", strong=True),
                Col(
                    "not_attending",
                    "Not attending",
                    fmt=lambda v, r: (
                        f"{theme.fmt_int(v)} <span class='muted'>({theme.fmt_pct(1 - r['attendance_rate'])})</span>"
                    ),
                    num=True,
                ),
                Col("places", "Places", fmt=lambda v, r: theme.fmt_int(v), num=True),
                Col("far_share", "> 1 km", fmt=lambda v, r: theme.fmt_pct(v), num=True),
                Col(
                    "bottleneck",
                    "Main bottleneck",
                    fmt=lambda v, r: theme.pill(v) if v else "–",
                ),
                Col(
                    "stability",
                    "Top-3 stable",
                    fmt=lambda v, r: theme.pill(stability_label(v), f"{v:.0%}"),
                ),
            ],
        ),
        unsafe_allow_html=True,
    )
    theme.note(
        f"Top-3 stability: share of {STABILITY_DRAWS} random weightings around the chosen "
        "weights in which the sector stays in the top 3 (green ≥ 80%, amber 40–80%, grey "
        f"below). Ranking and places: {status}; > 1 km: {far_status} "
        f"({result.distance_method.iloc[0] if len(result) else ''}); main bottleneck: "
        f"{diag_status}."
    )
    if user.can_decide:
        names = dict(zip(result.geo_id, result.name, strict=True))
        a1, a2 = st.columns([3, 1], vertical_alignment="bottom")
        pick = a1.multiselect(
            "Add sectors to your action plan",
            list(names),
            default=[g for g in st.session_state.get("plan_basket", []) if g in names],
            format_func=names.get,
            placeholder="Choose sectors",
        )
        if a2.button("Add to plan", type="primary", icon=":material/add:", width="stretch"):
            st.session_state["plan_basket"] = pick
            st.success(
                f"{len(pick)} sector(s) ready. Open Action plans to create or review the plan."
            )
        st.page_link("views/plan.py", label="Go to action plans", icon=":material/arrow_forward:")

# --- map (right of the ranking) and explanation (below) ----------------------------------
with (
    side,
    theme.panel(f"{districts[district_id]} map", "Priority score (higher = act first)", "pin"),
):
    geo = data.geojson("sector")
    maps.choropleth(
        geo,
        dict(zip(result.geo_id, result.score, strict=True)),
        "Priority score",
        lambda v: f"{v:.2f}",
        tooltip={
            r.geo_id: f"Rank {r.rank} · {theme.fmt_int(r.places)} places · {status}"
            for r in result.itertuples()
        },
        view=maps.view_for(geo, set(result.geo_id)),
        height=500,
        key="priority-map",
    )

with why_col, theme.panel("Why this order", "Top three sectors, component by component", "info"):
    st.markdown(
        "<span class='ir-note'><b>Weights used:</b> "
        + " · ".join(f"{COMPONENT_LABELS[c]} {w:.0%}" for c, w in used.items())
        + "</span>",
        unsafe_allow_html=True,
    )
    if "peer_gap" not in used:
        theme.note("Peer gap unavailable (peer model fallback): its weight is shared out.")
    for r in top3.itertuples():
        parts = " · ".join(
            f"{COMPONENT_LABELS[c]} {theme.ordinal(round(getattr(r, f'pct_{c}') * 100))} pct."
            for c in used
        )
        st.markdown(
            f"**{r.rank}. {r.name}** {theme.pill(stability_label(r.stability))}  \n"
            f"<span class='ir-note'>{parts}</span>",
            unsafe_allow_html=True,
        )
    theme.note(
        "Percentiles compare sectors within the district, not absolute need. Estimates are "
        "ranges: sectors close in score can swap places."
    )
