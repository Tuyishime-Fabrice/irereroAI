"""Screen 4. Plan builder and tracker (TRACK): are we on track for 2029, what-if, decisions."""

import altair as alt
import pandas as pd
import streamlit as st

from irerero import audit
from irerero.config import (
    CHILDREN_PER_ROOM,
    COMPONENTS,
    GREEN,
    MILESTONE_YEAR,
    MUTED,
    NAVY,
    PRESETS,
    PROJECTION_YEARS,
    SIMULATED,
    STATUS_COLOURS,
    TARGET_2027,
    TARGET_YEAR,
    YEARBOOK_YEARS,
)
from irerero.plan import gap
from irerero.plan.frame import ranked
from irerero.track import forecast, plans
from irerero.ui import data, theme
from irerero.ui.roles import ANALYST, OFFICER, current

user = current()
eng = data.eng()
districts = data.districts()
if user.role == ANALYST:
    district_id = st.selectbox("District", list(districts), format_func=districts.get, key="plan-d")
else:
    district_id = user.district_id
target = data.target()

rows = data.table("forecast")
mine = rows[rows.geo_id == district_id]
simulated = (mine.status == SIMULATED).any()
status_label = SIMULATED if simulated else "model estimate"
summary = forecast.summary(rows, target).loc[district_id]
theme.header(
    f"Plan builder and tracker · {districts[district_id]}",
    f"Are we on track for {theme.fmt_pct(target)} by {TARGET_YEAR}, and what has been decided.",
    simulated=simulated,
)

# --- status -------------------------------------------------------------------------------
chip = theme.chip(summary.status, STATUS_COLOURS[summary.status])
st.markdown(f"#### {TARGET_YEAR} status {chip}", unsafe_allow_html=True)
projected = mine[mine.kind == "projected"].set_index("year")
observed = mine[mine.kind == "observed"].set_index("year")
latest_year = YEARBOOK_YEARS[-1]
sectors = data.sectors()
district_rows = sectors[sectors.district_id == district_id]
latest_pupils = float(observed.loc[latest_year, "pupils"])
kids = projected.children.astype(float)
c1, c2, c3, c4 = st.columns(4)
with c1:
    theme.card(
        f"Enrolment rate {latest_year}",
        theme.fmt_pct(summary.latest, 1),
        "MINEDUC yearbook / NISR projection",
        latest_year,
        SIMULATED if simulated else "observed",
        "pupils per child aged 3 to 5 (gross)",
    )
with c2:
    m = projected.loc[MILESTONE_YEAR]
    theme.card(
        f"Projected {MILESTONE_YEAR}",
        theme.fmt_pct(m.value, 1),
        "IrereroAI linear trend",
        MILESTONE_YEAR,
        status_label,
        f"80% range {theme.fmt_pct(m.low)}–{theme.fmt_pct(m.high)} · NST2 milestone "
        f"{theme.fmt_pct(TARGET_2027.value, 1)}",
    )
with c3:
    theme.card(
        f"Projected {TARGET_YEAR}",
        theme.fmt_pct(summary.projected, 1),
        "IrereroAI linear trend",
        TARGET_YEAR,
        status_label,
        f"80% range {theme.fmt_pct(summary.low)}–{theme.fmt_pct(summary.high)} · target "
        f"{theme.fmt_pct(target)}",
    )
with c4:
    need = forecast.places_per_year(
        latest_pupils, float(kids.loc[TARGET_YEAR]), target, len(PROJECTION_YEARS)
    )
    theme.card(
        "Places a year still needed",
        theme.fmt_int(need),
        "IrereroAI, from MINEDUC pupils",
        f"{PROJECTION_YEARS[0]}–{TARGET_YEAR}",
        status_label,
        f"about {theme.fmt_int(need / CHILDREN_PER_ROOM.value)} rooms a year",
    )
back = summary.backtest_error_pp
theme.note(
    f"Back-test: fitted on 2020/21–2023/24, the trend predicted {latest_year} within "
    f"{abs(back):.1f} points ({'inside' if summary.backtest_inside else 'outside'} its 80% "
    "range). Pupils include over-age children, so the rate is gross. MINEDUC counts are not "
    "added to census or NCDA figures."
)

# --- what-if ------------------------------------------------------------------------------
st.subheader("What if we add rooms?")
plan_list = plans.plans(eng, district_id)
plan_id = int(plan_list.plan_id.iat[0]) if len(plan_list) else None
plan_items = plans.items(eng, plan_id) if plan_id else pd.DataFrame()
approved_rooms = (
    int(plan_items[plan_items.decision.isin(["approved", "edited"])].rooms.sum())
    if len(plan_items)
    else 0
)
names = dict(zip(district_rows.geo_id, district_rows.name, strict=True))
w1, w2 = st.columns([2, 1])
with w1:
    chosen = st.multiselect(
        "Sectors to add rooms in",
        list(names),
        default=[g for g in plan_items.get("geo_id", []) if g in names][:5],
        format_func=names.get,
    )
with w2:
    total_rooms = st.number_input(
        f"Rooms added per year in total (from {MILESTONE_YEAR})",
        min_value=0,
        max_value=2000,
        value=max(approved_rooms // len(PROJECTION_YEARS[1:]), 1) if approved_rooms else 10,
        step=1,
        help="Approved plan rooms spread over the three school years to 2028/29 by default.",
    )
with_plan = forecast.whatif(projected.value, kids, total_rooms, MILESTONE_YEAR)
lands = float(with_plan.loc[TARGET_YEAR])
lands_status = forecast.status_for(lands, lands, target)
where = ", ".join(names[g] for g in chosen) if chosen else "the district"
st.markdown(
    f"Adding **{total_rooms} rooms a year** in {where} from {MILESTONE_YEAR}, every place "
    f"filled, the district reaches **{theme.fmt_pct(lands, 1)}** by {TARGET_YEAR} "
    f"{theme.chip(lands_status, STATUS_COLOURS[lands_status])}",
    unsafe_allow_html=True,
)
if chosen:
    added = total_rooms * len(PROJECTION_YEARS[1:]) * CHILDREN_PER_ROOM.value
    room_gap = int(gap.needs(district_rows[district_rows.geo_id.isin(chosen)], target).places.sum())
    if added > room_gap:
        st.warning(
            f"{added:,} places is more than the chosen sectors need to reach "
            f"{theme.fmt_pct(target)} ({room_gap:,}). Extra places may stay empty: spread the "
            "rooms to other sectors."
        )
if approved_rooms:
    theme.note(f"Approved and edited plan items add {approved_rooms} rooms in total.")

chart_rows = [
    {"year": y, "value": r.value, "series": "Observed", "low": None, "high": None}
    for y, r in observed.iterrows()
] + [
    {"year": y, "value": r.value, "series": "Trend", "low": r.low, "high": r.high}
    for y, r in projected.iterrows()
] + [{"year": y, "value": v, "series": "With added rooms", "low": None, "high": None}
     for y, v in with_plan.items()]  # fmt: skip
chart = pd.DataFrame(chart_rows)
last_obs = observed.value.iloc[-1]
bridge = pd.DataFrame(
    [
        {"year": latest_year, "value": last_obs, "series": s, "low": last_obs, "high": last_obs}
        for s in ("Trend", "With added rooms")
    ]
)
chart = pd.concat([bridge, chart], ignore_index=True)
order = list(YEARBOOK_YEARS) + list(PROJECTION_YEARS)
x = alt.X("year:N", sort=order, title="School year")
band = (
    alt.Chart(chart[chart.series == "Trend"])
    .mark_area(opacity=0.2, color=NAVY)
    .encode(x=x, y="low:Q", y2="high:Q")
)
lines = (
    alt.Chart(chart)
    .mark_line(point=True)
    .encode(
        x=x,
        y=alt.Y("value:Q", axis=alt.Axis(format="%"), title="Pre-primary enrolment rate"),
        color=alt.Color(
            "series:N",
            scale=alt.Scale(
                domain=["Observed", "Trend", "With added rooms"], range=[NAVY, MUTED, GREEN]
            ),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        strokeDash=alt.condition(alt.datum.series == "Trend", alt.value([5, 4]), alt.value([1, 0])),
        tooltip=["series", "year", alt.Tooltip("value:Q", format=".1%")],
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
    .mark_point(shape="cross", size=160, color="#D55E00", strokeWidth=3)
    .encode(x=x, y="value:Q", tooltip=["label"])
)
labels = (
    alt.Chart(targets)
    .mark_text(dx=8, dy=-10, align="left", color="#D55E00")
    .encode(x=x, y="value:Q", text="label")
)
st.altair_chart((band + lines + marks + labels).properties(height=320), use_container_width=True)
theme.note(f"Shaded: 80% prediction range of the trend. Status: {status_label}.")

# --- plan ---------------------------------------------------------------------------------
st.subheader("Plan")
diag = data.diagnosis_now(target).set_index("geo_id")
if plan_id is None:
    if user.can_decide:
        with st.form("create-plan"):
            st.markdown(
                "Start a plan from the ranked sectors. Each one becomes a recommendation for "
                "you to approve, edit or reject."
            )
            f1, f2, f3 = st.columns(3)
            preset = f1.selectbox("Priority preset", list(PRESETS), index=2)
            top_n = f2.number_input(
                "Top sectors", 1, len(district_rows), min(5, len(district_rows))
            )
            name = f3.text_input("Plan name", f"{districts[district_id]} pre-primary plan 2026-29")
            basket = [g for g in st.session_state.get("plan_basket", []) if g in names]
            if basket:
                st.caption("Also added from Sector profile: " + ", ".join(names[g] for g in basket))
            if st.form_submit_button("Create plan", type="primary"):
                weights = dict(zip(COMPONENTS, PRESETS[preset], strict=True))
                result, _ = ranked(district_rows, target, weights, stability=False)
                pick = result.head(int(top_n))
                extra = result[result.geo_id.isin(basket) & ~result.geo_id.isin(pick.geo_id)]
                pick = pd.concat([pick, extra])
                plans.create_plan(
                    eng,
                    user,
                    district_id,
                    name,
                    target,
                    preset,
                    weights,
                    [
                        {
                            **r,
                            "bottleneck": diag.at[r["geo_id"], "bottleneck"],
                            "intervention": diag.at[r["geo_id"], "intervention"],
                        }
                        for r in pick[
                            [
                                "geo_id",
                                "rank",
                                "places",
                                "rooms",
                                "caregivers_low",
                                "caregivers_high",
                            ]
                        ].to_dict(orient="records")
                    ],
                )
                st.session_state["plan_basket"] = []
                st.rerun()
    else:
        st.info("No plan has been created for this district yet.")
else:
    plan_row = plan_list.iloc[0]
    st.markdown(
        f"**{plan_row['name']}** · target {theme.fmt_pct(plan_row.target)} · preset "
        f"{plan_row.preset} · created {plan_row.created_at:%Y-%m-%d} by {plan_row.created_by}"
    )
    shown = plan_items
    if user.role == OFFICER:
        shown = plan_items[plan_items.geo_id == user.sector_id]
    counts = shown.decision.value_counts()
    st.caption(
        " · ".join(
            f"{k}: {counts.get(k, 0)}" for k in ("pending", "approved", "edited", "rejected")
        )
    )
    for item in shown.itertuples():
        title = (
            f"{item.rank}. {names.get(item.geo_id, item.geo_id)} — {item.bottleneck} · "
            f"{item.places:,} places · {item.rooms} rooms · {item.decision} · {item.status}"
        )
        with st.expander(title, expanded=item.decision == "pending" and user.can_decide):
            st.markdown(f"**Recommended action.** {item.intervention}")
            st.markdown(
                f"Places {item.places:,} · rooms {item.rooms} · caregivers "
                f"{item.caregivers_low}–{item.caregivers_high}"
            )
            if item.reason:
                st.markdown(f"**Reason recorded:** {item.reason}")
            if not user.can_decide:
                continue
            with st.form(f"decide-{item.id}"):
                d1, d2 = st.columns([1, 2])
                decision = d1.radio(
                    "Decision",
                    ["approve", "edit", "reject"],
                    horizontal=False,
                    key=f"dec-{item.id}",
                )
                places = d1.number_input(
                    "Places (for an edit)", 0, 100_000, int(item.places), key=f"pl-{item.id}"
                )
                reason = d2.text_area(
                    "Reason (required to edit or reject)", key=f"re-{item.id}", height=110
                )
                if st.form_submit_button("Record decision"):
                    try:
                        plans.decide(eng, user, item.id, decision, reason, places)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
            if item.decision in ("approved", "edited"):
                new = st.selectbox(
                    "Status",
                    plans.STATUSES,
                    index=plans.STATUSES.index(item.status),
                    key=f"st-{item.id}",
                )
                if new != item.status and st.button("Update status", key=f"stb-{item.id}"):
                    plans.set_status(eng, user, item.id, new)
                    st.rerun()

    st.subheader("Audit log")
    ids = [str(plan_id)] + [str(i) for i in plan_items.id]
    log = audit.read(eng)
    log = log[
        ((log.entity == "plan") & log.entity_id.isin([str(plan_id)]))
        | ((log.entity == "plan_item") & log.entity_id.isin(ids[1:]))
    ]
    st.dataframe(
        log[["at", "user_id", "role", "action", "entity_id", "reason"]].rename(
            columns={
                "at": "When (UTC)",
                "user_id": "User",
                "role": "Role",
                "action": "Action",
                "entity_id": "Item",
                "reason": "Reason",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
    theme.note("The audit log is append-only: entries cannot be edited or deleted.")
