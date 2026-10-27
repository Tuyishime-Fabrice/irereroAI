"""Screen 4. Plan builder and tracker (TRACK): are we on track for 2029, what-if, decisions."""

import pandas as pd
import streamlit as st

from irerero import audit
from irerero.config import (
    CHILDREN_PER_ROOM,
    COMPONENTS,
    MILESTONE_YEAR,
    PRESETS,
    SIMULATED,
    TARGET_2027,
    TARGET_2029,
    TARGET_YEAR,
    YEARBOOK_YEARS,
)
from irerero.learn import progress
from irerero.plan import gap
from irerero.plan.frame import ranked
from irerero.track import forecast, plans
from irerero.ui import charts, data, i18n, theme
from irerero.ui.i18n import t
from irerero.ui.roles import ANALYST, OFFICER, current
from irerero.ui.theme import Col

user = current()
eng = data.eng()
districts = data.districts()
ids_d = list(districts)
district_id = st.session_state.get("plan-d", ids_d[0]) if user.role == ANALYST else user.district_id
target = data.target()

rows = data.table("forecast")
mine = rows[rows.geo_id == district_id]
simulated = (mine.status == SIMULATED).any()
status_label = SIMULATED if simulated else "model estimate"
summary = forecast.summary(rows, target).loc[district_id]
projected = mine[mine.kind == "projected"].set_index("year")
observed = mine[mine.kind == "observed"].set_index("year")
latest_year = YEARBOOK_YEARS[-1]
sectors = data.sectors()
district_rows = sectors[sectors.district_id == district_id]
province = district_rows.province.iat[0] if len(district_rows) else ""
latest_pupils = float(observed.loc[latest_year, "pupils"])
kids = projected.children.astype(float)
names = dict(zip(district_rows.geo_id, district_rows.name, strict=True))
plan_list = plans.plans(eng, district_id)
plan_id = int(plan_list.plan_id.iat[0]) if len(plan_list) else None
plan_items = plans.items(eng, plan_id) if plan_id else pd.DataFrame()

theme.header(
    "Action plans & progress",
    t(
        "Track decisions, delivery and progress toward {target} by {year}.",
        target=theme.fmt_pct(target),
        year=TARGET_YEAR,
    ),
    simulated=simulated,
    crumbs=["Rwanda", province, districts[district_id], "Action plans & progress"],
    assistant="plan",
)
if user.role == ANALYST:
    with theme.panel(key="filters"):
        st.selectbox(t("District"), ids_d, format_func=districts.get, key="plan-d")

# --- NST2 banner --------------------------------------------------------------------------
first = observed.value.iloc[0]
delta = (summary.latest - first) * 100
m = projected.loc[MILESTONE_YEAR]
nst2 = TARGET_2029.value
# The strip names the NST2 target; the last column is the target set on the screens, which can
# differ from it.
target_label = (
    t("{year} target", year=TARGET_YEAR)
    if round(target, 3) == round(nst2, 3)
    else t("Your {year} target (NST2: {target})", year=TARGET_YEAR, target=theme.fmt_pct(nst2))
)
theme.stat_strip(
    t("NST2 target: {target} pre-primary enrolment by {year}", target=f"{nst2:.0%}", year=TARGET_YEAR),
    f"Gross rate (MINEDUC pupils per child aged 3–5) · {districts[district_id]} · "
    f"status: {status_label}",
    [
        (
            t("Current ({year})", year=latest_year),
            theme.fmt_pct(summary.latest, 1),
            f"{delta:+.1f} pts since {observed.index[0]}",
        ),
        (t("{year} milestone", year=MILESTONE_YEAR), f"{TARGET_2027.value:.1%}",
         f"projected {theme.fmt_pct(m.value, 1)}"),
        (target_label, theme.fmt_pct(target), theme.pill(summary.status)),
    ],
)  # fmt: skip

# --- KPIs ---------------------------------------------------------------------------------
# Only the school years not yet over count: places still needed are spread over those.
remaining = forecast.years_left()
first_year = remaining[0] if remaining else TARGET_YEAR
need = forecast.places_per_year(latest_pupils, float(kids.loc[TARGET_YEAR]), target, len(remaining))
approved = (
    plan_items[plan_items.decision.isin(["approved", "edited"])] if len(plan_items) else plan_items
)
approved_rooms = int(approved.rooms.sum()) if len(approved) else 0
training = progress.summary(eng)
training = training[training.district_id == district_id]
if user.role == OFFICER:
    training = training[training.sector_id == user.sector_id]
k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi(t("Projected {year}", year=TARGET_YEAR), theme.fmt_pct(summary.projected, 1), "IrereroAI linear trend",
              TARGET_YEAR, status_label, f"80% range {theme.fmt_pct(summary.low)}–{theme.fmt_pct(summary.high)}",
              "trend", "blue")  # fmt: skip
with k2:
    theme.kpi("Places a year still needed", theme.fmt_int(need), "IrereroAI, from MINEDUC pupils",
              f"{first_year}–{TARGET_YEAR}", status_label,
              f"about {theme.fmt_int(need / CHILDREN_PER_ROOM.value)} rooms a year", "rooms", "gold")  # fmt: skip
with k3:
    if len(plan_items):
        counts = plan_items.decision.value_counts()
        detail = (f"{counts.get('approved', 0) + counts.get('edited', 0)} approved · "
                  f"{counts.get('pending', 0)} pending · {counts.get('rejected', 0)} rejected")  # fmt: skip
        value = str(len(plan_items))
    else:
        detail, value = "no plan yet", "0"
    theme.kpi(
        "Plan items",
        value,
        "District plan (user input)",
        None,
        "user input",
        detail,
        "clipboard",
        "navy",
    )
with k4:
    req = training[training.required] if len(training) else training
    if len(req):
        theme.kpi("Required training completed", theme.fmt_pct(req.completed.mean()),
                  "LEARN pilot", "2026", SIMULATED, f"{int(req.completed.sum())} of {len(req)} courses · "
                  f"{int(req.overdue.sum())} overdue", "cap", "purple")  # fmt: skip
    else:
        theme.kpi("Required training completed", "–", "LEARN pilot", None, None,
                  "pilot runs in Muhanga only", "cap", "purple")  # fmt: skip

# --- trend with what-if, and recent decisions ---------------------------------------------
left, right = st.columns([3, 2])
with (
    left,
    theme.panel(
        "Enrolment trend and what-if",
        f"{districts[district_id]} · observed, trend with 80% range, and added rooms",
        "trend",
    ),
):
    w1, w2 = st.columns([2, 1])
    chosen = w1.multiselect(
        t("Sectors to add rooms in"),
        list(names),
        default=[g for g in plan_items.get("geo_id", []) if g in names][:5],
        format_func=names.get,
    )
    total_rooms = w2.number_input(
        t("Rooms a year (from {year})", year=first_year),
        min_value=0,
        max_value=2000,
        value=max(approved_rooms // max(len(remaining), 1), 1) if approved_rooms else 10,
        step=1,
        help=f"Approved plan rooms spread over the {len(remaining)} school years left to "
        f"{TARGET_YEAR} by default.",
    )
    # New places count only up to what the chosen sectors (or the district) need, and not in
    # Demand sectors, where a school is near but children do not attend: rooms alone stay empty.
    scope = district_rows[district_rows.geo_id.isin(chosen)] if chosen else district_rows
    scope_needs = gap.needs(scope, target).set_index("geo_id")
    main_bottleneck = data.diagnosis_now(target).set_index("geo_id").bottleneck
    room_gap = forecast.fillable_places(scope_needs.places, main_bottleneck)
    demand = [
        names.get(g, g)
        for g, n in scope_needs.places.items()
        if n > 0 and main_bottleneck.get(g) == "DEMAND"
    ]
    with_plan = forecast.whatif(projected.value, kids, total_rooms, first_year, max_places=room_gap)
    st.markdown(charts.trend_legend(with_plan=True), unsafe_allow_html=True)
    st.altair_chart(
        charts.trend(observed, projected, target, with_plan, height=300), width="stretch"
    )
    lands = float(with_plan.loc[TARGET_YEAR])
    lands_status = forecast.status_for(lands, lands, target)
    where = ", ".join(names[g] for g in chosen) if chosen else "the district"
    st.markdown(
        f"Adding **{total_rooms} rooms a year** in {where} from {first_year}, every needed "
        f"place filled, the district reaches **{theme.fmt_pct(lands, 1)}** by {TARGET_YEAR} "
        f"{theme.pill(lands_status)}",
        unsafe_allow_html=True,
    )
    if demand:
        theme.note(
            f"Not counted: rooms in {', '.join(demand)}. The bottleneck there is Demand: a school "
            "is near but children do not attend, so new rooms alone would stay empty."
        )
    added = total_rooms * len(remaining) * CHILDREN_PER_ROOM.value
    if added > room_gap:
        st.warning(
            f"{added:,} places is more than {'the chosen sectors' if chosen else 'the district'} "
            f"can fill to reach {theme.fmt_pct(target)} ({room_gap:,}). Extra places may stay "
            f"empty, so the projection counts at most {room_gap:,}"
            + (": spread the rooms to other sectors." if chosen else ".")
        )
    back = summary.backtest_error_pp
    theme.note(
        f"Back-test: fitted on 2020/21–2023/24, the trend predicted {latest_year} within "
        f"{abs(back):.1f} points ({'inside' if summary.backtest_inside else 'outside'} its 80% "
        f"range). Approved and edited plan items add {approved_rooms} rooms. Status: {status_label}."
    )

ACTION_TEXT = {
    "plan.create": ("Plan created", "navy"),
    "plan_item.add": ("Added to plan", "navy"),
    "plan_item.approve": ("Approved", "teal"),
    "plan_item.edit": ("Edited", "blue"),
    "plan_item.reject": ("Rejected", "rose"),
    "plan_item.status": ("Status changed", "gold"),
}
log = audit.read(eng)
item_ids = [str(i) for i in plan_items.id] if len(plan_items) else []
log = log[
    ((log.entity == "plan") & (log.entity_id == str(plan_id)))
    | ((log.entity == "plan_item") & log.entity_id.isin(item_ids))
]
item_sector = dict(zip(item_ids, plan_items.geo_id, strict=True)) if len(plan_items) else {}
with right, theme.panel("Recent decisions & updates", "From the append-only audit log", "clock"):
    entries = []
    for r in log.head(7).itertuples():
        label, tone = ACTION_TEXT.get(r.action, (r.action, "slate"))
        sector = names.get(item_sector.get(r.entity_id, ""), "") if r.entity == "plan_item" else ""
        extra = ""
        if r.action == "plan_item.status" and isinstance(r.after, dict):
            extra = f" → {r.after.get('status')}"
        if r.action == "plan_item.edit" and isinstance(r.after, dict):
            extra = f" → {theme.fmt_int(r.after.get('places'))} places"
        what = f"{label}{': ' + sector if sector else ''}{extra}"
        why = theme.text(r.reason) + f" · {r.role.replace('_', ' ')}"
        entries.append((f"{r.at:%d %b %Y, %H:%M} UTC", what, why.strip(" ·"), tone))
    # The newest entry glows once when it was written moments ago, i.e. a decision just recorded.
    just_now = len(log) and (audit.now() - log["at"].iloc[0]).total_seconds() < 30
    fresh = ("a" if len(log) % 2 else "b") if just_now else ""
    st.markdown(theme.timeline(entries, fresh), unsafe_allow_html=True)
    if len(log) > 7:
        theme.note(f"{len(log) - 7} older entries in the full audit log below.")

# --- plan ---------------------------------------------------------------------------------
diag = data.diagnosis_now(target).set_index("geo_id")


def as_items(rows: pd.DataFrame) -> list[dict]:
    """Ranked sector rows as plan items, with their bottleneck and suggested action."""
    columns = ["geo_id", "rank", "places", "rooms", "caregivers_low", "caregivers_high"]
    return [
        {
            **r,
            "bottleneck": diag.at[r["geo_id"], "bottleneck"],
            "intervention": diag.at[r["geo_id"], "intervention"],
        }
        for r in rows[columns].to_dict(orient="records")
    ]


def plan_form(key: str, intro: str, name: str, label: str, replaces: int | None = None) -> None:
    """The form that starts a plan, or a new version of one, from the ranked sectors and the
    sectors added from the ranking or Sector diagnosis."""
    with st.form(key, border=False):
        st.markdown(intro)
        f1, f2, f3 = st.columns(3)
        preset = f1.selectbox(
            t("Priority preset"), list(PRESETS), index=2, format_func=i18n.shown(PRESETS)
        )
        top_n = f2.number_input(t("Top sectors"), 1, len(district_rows), min(5, len(district_rows)))
        name = f3.text_input(t("Plan name"), name)
        basket = [g for g in st.session_state.get("plan_basket", []) if g in names]
        if basket:
            st.caption(
                "Also added from the ranking or Sector diagnosis: "
                + ", ".join(names[g] for g in basket)
            )
        if st.form_submit_button(label, type="primary", icon=":material/add:"):
            weights = dict(zip(COMPONENTS, PRESETS[preset], strict=True))
            result, _ = ranked(district_rows, target, weights, stability=False)
            pick = result.head(int(top_n))
            extra = result[result.geo_id.isin(basket) & ~result.geo_id.isin(pick.geo_id)]
            pick = pd.concat([pick, extra])
            plans.create_plan(
                eng, user, district_id, name, target, preset, weights, as_items(pick), replaces
            )
            st.session_state["plan_basket"] = []
            st.rerun()


with theme.panel(
    "Action plan",
    "Recommendations become plan items; the district planner decides each one.",
    "clipboard",
):
    if plan_id is None:
        if user.can_decide:
            plan_form(
                "create-plan",
                "Start a plan from the ranked sectors. Each one becomes a recommendation for "
                "you to approve, edit or reject.",
                f"{districts[district_id]} pre-primary plan 2026-29",
                t("Create plan"),
            )
        else:
            st.markdown(
                theme.empty_state("No plan has been created for this district yet."),
                unsafe_allow_html=True,
            )
    else:
        # The newest version is the plan in force; earlier versions stay readable, read-only.
        viewing = plan_id
        if len(plan_list) > 1:
            label = {
                int(r.plan_id): f"{r['name']} · {r.created_at:%d %b %Y, %H:%M}"
                + (" (current)" if i == 0 else "")
                for i, (_, r) in enumerate(plan_list.iterrows())
            }
            viewing = st.selectbox(
                t("Plan version"), list(label), format_func=label.get, key=f"version-{district_id}"
            )
        current = viewing == plan_id
        plan_row = plan_list.set_index("plan_id").loc[viewing]
        if not current:
            plan_items = plans.items(eng, viewing)
            item_ids = [str(i) for i in plan_items.id] if len(plan_items) else []
            log = audit.read(eng)
            log = log[
                ((log.entity == "plan") & (log.entity_id == str(viewing)))
                | ((log.entity == "plan_item") & log.entity_id.isin(item_ids))
            ]
            theme.note(
                "Earlier version: read-only. Its decisions stay as recorded, and in the audit log."
            )
        editable = user.can_decide and current
        st.markdown(
            f"**{plan_row['name']}** · target {theme.fmt_pct(plan_row.target)} · preset "
            f"{plan_row.preset} · created {plan_row.created_at:%d %b %Y} by {plan_row.created_by}"
        )
        in_plan = set(plan_items.geo_id) if len(plan_items) else set()
        basket = [
            g for g in st.session_state.get("plan_basket", []) if g in names and g not in in_plan
        ]
        if editable and basket:
            b1, b2 = st.columns([3, 1], vertical_alignment="center")
            b1.markdown(
                "Added from the ranking or Sector diagnosis, not yet in this plan: "
                + ", ".join(names[g] for g in basket)
            )
            if b2.button(
                t("Add {n} to this plan", n=len(basket)),
                type="primary",
                icon=":material/add:",
                width="stretch",
            ):
                # The plan's own preset and target, so new items match the ones already in it.
                weights = dict(
                    zip(
                        COMPONENTS,
                        PRESETS.get(plan_row.preset, PRESETS["Balanced"]),
                        strict=True,
                    )
                )
                result, _ = ranked(district_rows, float(plan_row.target), weights, stability=False)
                plans.add_items(eng, user, plan_id, as_items(result[result.geo_id.isin(basket)]))
                st.session_state["plan_basket"] = []
                st.rerun()
        shown = plan_items
        if user.role == OFFICER:
            shown = plan_items[plan_items.geo_id == user.sector_id]
        st.markdown(
            theme.table(
                shown.to_dict(orient="records"),
                [
                    Col("rank", "Rank", num=True),
                    Col("geo_id", "Sector", fmt=lambda v, r: names.get(v, v), strong=True),
                    Col("bottleneck", "Bottleneck", fmt=lambda v, r: theme.pill(v)),
                    Col("places", "Places", fmt=lambda v, r: theme.fmt_int(v), num=True),
                    Col("rooms", "Rooms", fmt=lambda v, r: theme.fmt_int(v), num=True),
                    Col(
                        "caregivers_low",
                        "Caregivers",
                        fmt=lambda v, r: f"{v}–{r['caregivers_high']}",
                        num=True,
                    ),
                    Col("decision", "Decision", fmt=lambda v, r: theme.pill(v)),
                    Col(
                        "status",
                        "Delivery",
                        fmt=lambda v, r: (
                            theme.pill(v) if r["decision"] in ("approved", "edited") else "–"
                        ),
                    ),
                ],
                pin=True,
                empty="No items for your sector in this plan.",
            ),
            unsafe_allow_html=True,
        )
        if editable and len(shown):
            st.markdown("**Decide each recommendation**")
            first_pending = next(
                (i.id for i in shown.itertuples() if i.decision == "pending"), None
            )
            for item in shown.itertuples():
                title = (
                    f"{item.rank}. {names.get(item.geo_id, item.geo_id)} · "
                    f"{theme.PILLS.get(item.bottleneck, ('', item.bottleneck))[1]} · {item.places:,} places · "
                    f"{item.decision}"
                )
                with st.expander(title, expanded=item.id == first_pending):
                    st.markdown(f"**Recommended action.** {item.intervention}")
                    if theme.text(item.reason):
                        theme.note(f"Reason recorded: {item.reason}")
                    with st.form(f"decide-{item.id}", border=False):
                        d1, d2 = st.columns([1, 2])
                        decision = d1.radio(
                            t("Decision"),
                            ["approve", "edit", "reject"],
                            key=f"dec-{item.id}",
                            format_func=i18n.shown(plans.DECISIONS),
                        )
                        places = d1.number_input(
                            t("Places (for an edit)"),
                            0,
                            100_000,
                            int(item.places),
                            key=f"pl-{item.id}",
                        )
                        reason = d2.text_area(
                            t("Reason (required to edit or reject)"),
                            key=f"re-{item.id}",
                            height=110,
                        )
                        if st.form_submit_button(t("Record decision"), type="primary"):
                            try:
                                plans.decide(eng, user, item.id, decision, reason, places)
                                st.rerun()
                            except ValueError as error:
                                st.error(str(error))
                    if item.decision in ("approved", "edited"):
                        c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
                        new = c1.selectbox(
                            t("Delivery status"),
                            plans.STATUSES,
                            format_func=i18n.shown(plans.STATUSES),
                            index=plans.STATUSES.index(item.status),
                            key=f"st-{item.id}-{i18n.lang()}",  # shown text follows the language
                        )
                        if c2.button(
                            t("Update status"),
                            key=f"stb-{item.id}",
                            disabled=new == item.status,
                        ):
                            plans.set_status(eng, user, item.id, new)
                            st.rerun()
        elif not user.can_decide:
            theme.note(
                "Read-only: only the district planner approves, edits or rejects plan items."
            )
        if editable:
            with st.expander(t("Start a new version")):
                plan_form(
                    "new-version",
                    "A new version starts again from the ranked sectors, at the current target. "
                    "This version stays read-only, with its decisions and audit log.",
                    f"{plan_row['name']} (new version)",
                    t("Create new version"),
                    replaces=plan_id,
                )

        with st.expander(t("Full audit log for this plan")):
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
                width="stretch",
            )
            theme.note("The audit log is append-only: entries cannot be edited or deleted.")

# --- training -----------------------------------------------------------------------------
with theme.panel("Training tracker", "Required LEARN courses by sector · aggregates only", "cap"):
    if training.empty:
        st.markdown(
            theme.empty_state(
                "No LEARN data for this district: the pilot runs in Muhanga.", "book"
            ),
            unsafe_allow_html=True,
        )
    else:
        by_sector = progress.aggregate(training, "sector_id")
        flagged = training[training.status == "recommended"].groupby("sector_id").size()
        by_sector["waiting"] = [int(flagged.get(g, 0)) for g in by_sector.sector_id]
        st.markdown(
            theme.table(
                by_sector.to_dict(orient="records"),
                [
                    Col("sector_id", "Sector", fmt=lambda v, r: names.get(v, v), strong=True),
                    Col("caregivers", "Caregivers", num=True),
                    Col("required", "Required assigned", num=True),
                    Col("completed", "Completed", num=True),
                    Col(
                        "overdue",
                        "Overdue",
                        fmt=lambda v, r: theme.pill("Medium", str(v)) if v else "0",
                        num=True,
                    ),
                    Col("waiting", "Waiting for officer", num=True),
                    Col(
                        "share_completed", "Completed", fmt=lambda v, r: theme.fmt_pct(v), num=True
                    ),
                ],
            ),
            unsafe_allow_html=True,
        )
        theme.note(
            "Simulated pilot data. Completion of required training feeds the capacity factor in "
            f"DIAGNOSE. {progress.QUIZ_NOTE}"
        )
