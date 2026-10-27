"""Screen 1. Overview: where the formal pre-primary gap is, and whether districts are on track."""

import streamlit as st

from irerero.config import STATUS_COLOURS, TARGET_2029, TARGET_YEAR
from irerero.plan import gap
from irerero.plan.frame import distance_status, status_of
from irerero.track import forecast, plans
from irerero.ui import assistant, charts, data, i18n, maps, theme
from irerero.ui.i18n import t
from irerero.ui.roles import PLANNER, current
from irerero.ui.theme import Col

user = current()
sectors = data.sectors()
forecast_rows = data.table("forecast")
# each part keeps its own status: the estimate (census, projections), the distance layer
# (school points) and the outlook (yearbook trend) become real at different times
status = status_of(sectors)
far_status = distance_status(sectors)
track_status = status_of(forecast_rows)
simulated = "simulated" in (status, far_status, track_status)
source = "IrereroAI 2026 estimate"

theme.topbar(["Rwanda", "Overview"])
assistant.hero(user, simulated, sr_title="Early Childhood Development Overview")

# --- filters ------------------------------------------------------------------------------
with theme.panel(key="filters"):
    f1, f2, f3 = st.columns([1, 1, 1])
    provinces = ["All provinces", *sorted(sectors.province.dropna().unique())]
    province = i18n.select(f1, t("Province"), provinces, key="ov-province")
    target_pct = f2.slider(
        t("Target attendance (%)"),
        30,
        90,
        round(data.target() * 100),
        help=f"Default {theme.fmt_pct(TARGET_2029.value)}: {TARGET_2029.citation}",
    )
    st.session_state["target_pct"] = target_pct
    if target_pct != round(TARGET_2029.value * 100):
        theme.note(
            f"Planning at {target_pct}%: the numbers below use this target, not the NST2 "
            f"{theme.fmt_pct(TARGET_2029.value)}."
        )
    theme.measure_note()
    f3.selectbox(
        t("Reference year"),
        ["2026 estimate (census 2022 base)"],
        disabled=True,
        help="Estimates are calibrated to NISR projections for 2026.",
    )
target = target_pct / 100
scope = sectors if province == "All provinces" else sectors[sectors.province == province]
needs = gap.needs(scope, target)
place = "Rwanda" if province == "All provinces" else province

# --- KPIs ---------------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi(
        "Children aged 3–5 (2026)",
        theme.fmt_int(needs.children_3_5.sum()),
        source,
        "2026",
        status,
        f"range {theme.fmt_int(needs.low.sum())} to {theme.fmt_int(needs.high.sum())} · {place}",
        "users",
        "teal",
    )
with k2:
    rate = needs.attending.sum() / needs.children_3_5.sum()
    theme.kpi(
        "Attending pre-primary",
        theme.fmt_pct(rate, 1),
        source,
        "2026",
        status,
        f"≈ {theme.fmt_int(needs.attending.sum())} children",
        "school",
        "blue",
    )
with k3:
    theme.kpi(
        t("Places needed for {target}", target=theme.fmt_pct(target)),
        theme.fmt_int(needs.places.sum()),
        source,
        "2026",
        status,
        f"{theme.fmt_int(needs.rooms.sum())} rooms at 30 children each",
        "target",
        "gold",
    )
with k4:
    far = (needs.far_share * needs.children_3_5).sum() / needs.children_3_5.sum()
    method = needs.distance_method.mode().iat[0] if len(needs) else ""
    theme.kpi(
        "Children > 1 km from a school",
        theme.fmt_pct(far),
        "IrereroAI distance layer",
        "2026",
        far_status,
        method,
        "route",
        "rose",
    )

track_all = forecast.summary(forecast_rows, target)
track = track_all.drop(index=forecast.NATIONAL)
in_scope = set(scope.district_id)
track = track[track.index.isin(in_scope)]

# --- map and outlook ----------------------------------------------------------------------
left, right = st.columns([3, 2])
with left, theme.panel("Where the gap is", f"{place} · children aged 3–5", "pin"):
    views = [f"{TARGET_YEAR} status", "Places needed", "Attendance rate"]
    view = (
        st.segmented_control(
            "Map layer",
            views,
            default=views[0],
            label_visibility="collapsed",
            key="map-view",
            format_func=i18n.shown(views, {views[0]: t("{year} status", year=TARGET_YEAR)}),
        )
        or views[0]  # clicking the selected segment clears it; keep showing a layer
    )
    geo_d, geo_s = data.geojson("district"), data.geojson("sector")
    zoom = maps.view_for(geo_d, in_scope) if province != "All provinces" else None
    if view.endswith("status"):
        maps.choropleth(
            geo_d,
            track.projected.to_dict(),
            f"Projected {TARGET_YEAR} enrolment",
            lambda v: theme.fmt_pct(v),
            tooltip={
                g: f"{r.status} · 80% range {theme.fmt_pct(r.low)}–{theme.fmt_pct(r.high)} · "
                f"{track_status}"
                for g, r in track.iterrows()
            },
            colours={g: STATUS_COLOURS[s] for g, s in track.status.items()},
            view=zoom,
            height=400,
            key="national-status",
        )
        counts = track.status.value_counts()
        maps.legend(
            [(c, f"{k} ({counts.get(k, 0)})") for k, c in STATUS_COLOURS.items()],
            f"Districts by projected {TARGET_YEAR} status against {theme.fmt_pct(target)}",
        )
    elif view == "Places needed":
        maps.choropleth(
            geo_s,
            dict(zip(needs.geo_id, needs.places, strict=True)),
            t("Places needed for {target}", target=theme.fmt_pct(target)),
            theme.fmt_int,
            tooltip={
                r.geo_id: f"{r.district} · {theme.fmt_pct(r.attendance_rate)} attending · {status}"
                for r in needs.itertuples()
            },
            view=zoom,
            height=400,
            key="national-sectors",
        )
    else:
        by_district = needs.groupby("district_id").agg(
            children=("children_3_5", "sum"), attending=("attending", "sum")
        )
        rates = by_district.attending / by_district.children
        maps.choropleth(
            geo_d,
            rates.to_dict(),
            "Attending pre-primary (2026)",
            lambda v: theme.fmt_pct(v),
            tooltip={k: status for k in rates.index},
            view=zoom,
            height=400,
            key="national-districts",
        )

with (
    right,
    theme.panel(
        t("{year} target outlook", year=TARGET_YEAR), "Pre-primary enrolment, Rwanda", "trend"
    ),
):
    national = forecast_rows[forecast_rows.geo_id == forecast.NATIONAL]
    observed = national[national.kind == "observed"].set_index("year")
    projected = national[national.kind == "projected"].set_index("year")
    st.markdown(charts.trend_legend(), unsafe_allow_html=True)
    st.altair_chart(charts.trend(observed, projected, target, height=320), width="stretch")
    nat = track_all.loc[forecast.NATIONAL]
    st.markdown(
        f"Projected **{theme.fmt_pct(nat.projected, 1)}** by {TARGET_YEAR} "
        f"(80% range {theme.fmt_pct(nat.low)}–{theme.fmt_pct(nat.high)}) "
        f"{theme.pill(nat.status)}",
        unsafe_allow_html=True,
    )
    theme.note(
        "Gross rate: MINEDUC pre-primary pupils per child aged 3–5. Linear trend with an 80% "
        f"prediction range. Status: {track_status}."
    )

# --- districts and actions ----------------------------------------------------------------
left, right = st.columns([3, 2])
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
by["not_attending"] = by.children - by.attending
by["rate"] = by.attending / by.children
by["track"] = by.district_id.map(track.status)
by.insert(0, "rank", range(1, len(by) + 1))
with (
    left,
    theme.panel(
        "Districts needing attention first",
        f"Ranked by places needed to reach {theme.fmt_pct(target)} · {place}",
        "chart",
    ),
):
    show_all = st.toggle(t("Show all districts"), value=False)
    rows_html = by if show_all else by.head(8)
    st.markdown(
        theme.table(
            rows_html.to_dict(orient="records"),
            [
                Col("rank", "Rank", num=True),
                Col("district", "District", strong=True),
                Col(
                    "province",
                    "Province",
                    fmt=lambda v, r: f'<span class="muted">{v.replace(" Province", "")}</span>',
                ),
                Col(
                    "not_attending",
                    "Children not attending",
                    fmt=lambda v, r: f"{theme.fmt_int(v)} ({theme.fmt_pct(1 - r['rate'])})",
                    num=True,
                ),
                Col("places", "Places needed", fmt=lambda v, r: theme.fmt_int(v), num=True),
                Col("rooms", "Rooms", fmt=lambda v, r: theme.fmt_int(v), num=True),
                Col(
                    "track",
                    t("{year} status", year=TARGET_YEAR),
                    fmt=lambda v, r: theme.pill(v) if v else "–",
                ),
            ],
            pin=True,
        ),
        unsafe_allow_html=True,
    )
    theme.note(
        f"Children, places and rooms: {status}; {TARGET_YEAR} status: {track_status}. Rooms and "
        "places: National ECD Standards (2024). Hover a KPI for its source and year."
    )

with (
    right,
    theme.panel("Planner actions", "Pending decisions in your district's plan", "clipboard"),
):
    if user.role == PLANNER and user.district_id:
        plan_list = plans.plans(data.eng(), user.district_id)
        if len(plan_list):
            items = plans.items(data.eng(), int(plan_list.plan_id.iat[0]))
            names = data.table("geo_unit").set_index("geo_id").name
            pending = items[items.decision == "pending"].head(5)
            decided = items[items.decision != "pending"]
            if len(pending):
                st.markdown(
                    theme.table(
                        pending.to_dict(orient="records"),
                        [
                            Col("geo_id", "Sector", fmt=lambda v, r: names.get(v, v), strong=True),
                            Col("bottleneck", "Bottleneck", fmt=lambda v, r: theme.pill(v)),
                            Col("places", "Places", fmt=lambda v, r: theme.fmt_int(v), num=True),
                        ],
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    theme.empty_state("Every item has a decision.", "check"), unsafe_allow_html=True
                )
            theme.note(f"{len(decided)} of {len(items)} items decided.")
        else:
            st.markdown(
                theme.empty_state("No plan yet for your district. Start one from the ranking."),
                unsafe_allow_html=True,
            )
        st.page_link("views/plan.py", label=t("Open action plans"), icon=":material/arrow_forward:")
    else:
        st.markdown(
            theme.empty_state(
                "Plans are made by district planners. Pick a district in Action plans to read one."
            ),
            unsafe_allow_html=True,
        )
        st.page_link("views/plan.py", label=t("Open action plans"), icon=":material/arrow_forward:")
