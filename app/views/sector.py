"""Screen 3. Sector diagnosis (DIAGNOSE): what is holding pre-primary attendance back here."""

from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from irerero.config import MODEL, PROVISIONAL, SIMULATED, WEAK_FACTOR
from irerero.diagnose.features import LABELS, LEVEL
from irerero.diagnose.peer import MODEL_LABELS
from irerero.diagnose.rules import COURSES, FACTOR_LABELS
from irerero.plan import gap
from irerero.track import plans
from irerero.ui import data, theme
from irerero.ui.i18n import t
from irerero.ui.roles import ANALYST, OFFICER, current
from irerero.ui.theme import SERIES, Bar, Col

user = current()
target = data.target()
diag = data.diagnosis_now(target)
districts = data.districts()
ids_d = list(districts)

if user.role == OFFICER:
    district_id = user.district_id
elif user.role == ANALYST:
    district_id = st.session_state.get("sector-district", ids_d[0])
else:
    district_id = user.district_id
options = diag[diag.district_id == district_id].sort_values("name")
names = dict(zip(options.geo_id, options.name, strict=True))
ids = list(names)
if user.role == OFFICER:
    geo_id = user.sector_id
else:
    picked = st.session_state.get("sector-pick") or st.session_state.get("sector_id")
    geo_id = picked if picked in ids else ids[0]
st.session_state["sector_id"] = geo_id

row = diag.set_index("geo_id").loc[geo_id]
peers = diag[diag.district_id == district_id]
# the estimate, the peer benchmark and the diagnosis rules each keep their own status, and
# each factor is simulated while one of its indicators is
est_status, peer_status, status = row.estimate_status, row.peer_status, row.status
stand_ins = set(row.simulated_inputs)
partial = set(row.provisional_inputs)  # shown, not scored: e.g. distance from a partial list
FACTOR_INPUTS = {
    "access": {"nonattendance", "far_share"},
    "capacity": {"pupils_per_teacher", "pupils_per_classroom", "qualified_share"},
    "wellbeing": {"stunting"},
    "home": {"water_share", "sanitation_share", "women_secondary_share"},
    "poverty": {"poverty"},
}


def factor_status(factor: str) -> str:
    return SIMULATED if FACTOR_INPUTS[factor] & stand_ins else MODEL


simulated = SIMULATED in (est_status, peer_status, status)
run = data.table("model_run")
chosen = run[run.chosen].iloc[0] if len(run) else None
fallback = bool(row.fallback)
province = row.province if isinstance(row.province, str) else ""

theme.header(
    "Sector diagnosis",
    "Understand what is holding early childhood development back.",
    simulated=simulated,
    crumbs=["Rwanda", province, districts[district_id], row["name"]],
    assistant="sector",
)

# --- selectors ----------------------------------------------------------------------------
with theme.panel(key="filters"):
    f1, f2, f3 = st.columns(3)
    if user.role == ANALYST:
        f1.selectbox(t("District"), ids_d, format_func=districts.get, key="sector-district")
    else:
        f1.selectbox(t("District"), [district_id], format_func=districts.get, disabled=True)
    if user.role == OFFICER:
        f2.selectbox(t("Sector"), [geo_id], format_func=lambda g: row["name"], disabled=True,
                     help="Sector officers see their own sector.")  # fmt: skip
    else:
        f2.selectbox(
            t("Sector"), ids, index=ids.index(geo_id), format_func=names.get, key="sector-pick"
        )
    f3.selectbox(
        t("Diagnosis target"),
        [f"{target:.0%} by 2028/29"],
        disabled=True,
        help="Set the target on District priorities; it carries across screens.",
    )

# --- KPIs ---------------------------------------------------------------------------------
places = gap.places(target, row.children_3_5, row.attending)
k1, k2, k3, k4 = st.columns([1, 1, 1, 1.4])
with k1:
    theme.kpi("Children aged 3–5", theme.fmt_int(row.children_3_5), "IrereroAI 2026 estimate",
              "2026", est_status, f"range {theme.fmt_int(row.children_low)}–{theme.fmt_int(row.children_high)}",
              "users", "teal")  # fmt: skip
with k2:
    theme.kpi("Attending pre-primary", theme.fmt_pct(row.attendance_rate), "IrereroAI 2026 estimate",
              "2026", est_status, f"census 2022: {theme.fmt_pct(row.attendance_2022)}", "school", "blue")  # fmt: skip
with k3:
    theme.kpi("Target", theme.fmt_pct(target), "NST2", "2028/29", None,
              f"{theme.fmt_int(places)} places short", "target", "gold")  # fmt: skip
with k4:
    theme.alert(
        f"Main bottleneck: {theme.PILLS[row.bottleneck][1]}",
        row.intervention,
        "teal" if row.bottleneck == "NONE" else "rose",
    )

# --- factors and decision -----------------------------------------------------------------
left, right = st.columns([3, 2])
FACTOR_STYLE = {
    "access": ("home", "rose", "Places and distance to a school"),
    "capacity": ("users", "gold", "Teacher ratios, qualifications, LEARN training"),
    "wellbeing": ("heart", "teal", "Stunting, children under 5"),
    "home": ("droplet", "blue", "Water, sanitation, mothers' education"),
    "poverty": ("coins", "purple", "Household poverty rate"),
}
with (
    left,
    theme.panel(
        t("Key factors affecting ECD in {name}", name=row["name"]),
        "National percentile, 1 = worst · line marks the worst quarter",
        "layers",
    ),
):
    items = []
    for f, (ico, tone, sub) in FACTOR_STYLE.items():
        value = row["poverty_score"] if f == "poverty" else row[f]
        level = (
            ("sector" if row.poverty_level == "sector" else "district context")
            if f == "poverty"
            else ("district context" if f in ("capacity", "wellbeing") else "sector")
        )
        label = "no data" if pd.isna(value) else f"{value:.2f} · {level}"
        if not pd.isna(value) and value >= WEAK_FACTOR:
            label += " · worst quarter"
        if not pd.isna(value) and factor_status(f) == SIMULATED:
            label += " · simulated"
        if f == "access" and "far_share" in partial:
            label += " · distance not scored (provisional list)"
        items.append(Bar(FACTOR_LABELS[f], sub, value, label, ico, tone, theme.TONES[tone][1]))
    st.markdown(theme.bars(items, marker=WEAK_FACTOR), unsafe_allow_html=True)
    theme.note(
        "District context applies to every sector of the district and is not a sector value. "
        "Scores rank sectors (or districts); they are not shares of the gap."
    )

with right, theme.panel("Planner decision", "The rules suggest; a person decides.", "clipboard"):
    plan_list = plans.plans(data.eng(), district_id)
    in_plan = None
    if len(plan_list):
        items_df = plans.items(data.eng(), int(plan_list.plan_id.iat[0]))
        match = items_df[items_df.geo_id == geo_id]
        in_plan = match.iloc[0] if len(match) else None
    if in_plan is not None:
        st.markdown(
            f"In the district plan: {theme.pill(in_plan.decision)} {theme.pill(in_plan.status)}",
            unsafe_allow_html=True,
        )
        if theme.text(in_plan.reason):
            theme.note(f"Reason recorded: {in_plan.reason}")
    else:
        st.markdown(
            f"Not in the district plan yet {theme.pill('pending', 'Not decided')}",
            unsafe_allow_html=True,
        )
    for reason in row.reasons:
        st.markdown(f"<div class='ir-note'>• {escape(reason)}</div>", unsafe_allow_html=True)
    if user.can_decide:
        st.session_state.setdefault("plan_basket", [])
        at_target = places == 0  # no places to plan, so nothing to add
        if st.button(
            t("Add to action plan"),
            type="primary",
            icon=":material/add:",
            width="stretch",
            disabled=at_target,
            help="Already at the target: no places needed." if at_target else None,
        ):
            if geo_id not in st.session_state["plan_basket"]:
                st.session_state["plan_basket"].append(geo_id)
            st.success(f"{row['name']} added. Open Action plans to create or review the plan.")
    st.page_link(
        "views/plan.py", label=t("Review in action plans"), icon=":material/arrow_forward:"
    )
    theme.note(
        "Human review: this diagnosis applies explicit rules to estimates. A district planner approves, edits or rejects it, with the decision logged."
    )

# --- peer benchmark -----------------------------------------------------------------------
left, right = st.columns([3, 2])
model_name = MODEL_LABELS.get(chosen.model_id, "") if chosen is not None else ""
with (
    left,
    theme.panel(
        "Observed vs expected attendance",
        f"Census 2022 · expected from {'the district average' if fallback else model_name} · 80% interval",
        "chart",
    ),
):
    if fallback:
        st.info(
            "No peer model beat the district average, so each sector is compared with the "
            "average of the other sectors in its district."
        )
    chart = peers[["name", "observed", "expected", "low", "high"]].copy()
    chart["selected"] = chart.name == row["name"]
    base = alt.Chart(chart).encode(
        y=alt.Y(
            "name:N",
            sort=alt.EncodingSortField("observed", order="descending"),
            title=None,
            axis=alt.Axis(labelOverlap=False, labelLimit=140),
        )
    )
    interval = base.mark_rule(strokeWidth=7, opacity=0.3, color=SERIES[1]).encode(
        x=alt.X("low:Q", axis=alt.Axis(format="%"), title=None), x2="high:Q"
    )
    expected = base.mark_tick(color=SERIES[1], thickness=2, size=14).encode(x="expected:Q")
    observed = base.mark_point(filled=True, size=80, stroke="white", strokeWidth=1.5).encode(
        x="observed:Q",
        color=alt.condition(alt.datum.selected, alt.value(SERIES[2]), alt.value(SERIES[0])),
        shape=alt.condition(alt.datum.selected, alt.value("diamond"), alt.value("circle")),
        tooltip=[
            "name",
            alt.Tooltip("observed:Q", format=".0%"),
            alt.Tooltip("expected:Q", format=".0%"),
            alt.Tooltip("low:Q", format=".0%", title="interval low"),
            alt.Tooltip("high:Q", format=".0%", title="interval high"),
        ],
    )
    st.altair_chart(
        (interval + expected + observed).properties(height=max(220, 28 * len(chart))),
        width="stretch",
    )
    theme.note(
        f"Dot: observed (this sector: gold diamond). Bar: 80% interval; tick: expected value, "
        f"fitted without the sector's own district. Status: {peer_status}."
    )

with (
    right,
    theme.panel("What the model sees", "Top drivers · associated with, not caused by", "info"),
):
    st.markdown(
        f"**{row['name']}:** observed **{theme.fmt_pct(row.observed)}**, expected "
        f"**{theme.fmt_pct(row.expected)}** (80% interval {theme.fmt_pct(row.low)}–"
        f"{theme.fmt_pct(row.high)})."
    )
    if not fallback and isinstance(row.drivers, list) and row.drivers:
        top = max(abs(d["contribution_pp"]) for d in row.drivers) or 1
        bars_html = theme.bars(
            [
                Bar(
                    d["label"],
                    f"{'raises' if d['contribution_pp'] >= 0 else 'lowers'} the expectation",
                    abs(d["contribution_pp"]) / top,
                    f"{d['contribution_pp']:+.1f} points vs an average sector",
                    "trend",
                    "teal" if d["contribution_pp"] >= 0 else "rose",
                    SERIES[1] if d["contribution_pp"] >= 0 else theme.SIM_RED,
                )
                for d in row.drivers
            ],
            marker=None,
        )
        st.markdown(bars_html, unsafe_allow_html=True)
    else:
        st.markdown(
            theme.empty_state("No drivers: the district average is the benchmark."),
            unsafe_allow_html=True,
        )


# --- evidence -----------------------------------------------------------------------------
def level(score: float) -> str:
    if score != score:
        return "Low"
    return "High" if score >= WEAK_FACTOR else ("Medium" if score >= 0.5 else "Low")


def pct(key: str) -> str:
    v = row.get(key)
    return "–" if v is None or pd.isna(v) else f"{v:.0%}"


evidence = [
    {
        "factor": "Place gap (access)",
        "evidence": f"{pct('nonattendance')} of children aged 3–5 not attending; "
        + (
            f"at most {pct('far_share_listed')} live more than 1 km from a listed school "
            "(provisional list of standalone pre-primary schools; not used in the bottleneck)."
            if "far_share" in partial
            else f"{pct('far_share')} live more than 1 km from a school."
        ),
        "level": level(row.access),
        "action": "Build or expand rooms where children are far from a school; expand nearby schools otherwise.",
        "source": "IrereroAI estimate (census 2022, NISR projections"
        + ("; MINEDUC school list)" if "far_share" in partial else ", OSM)"),
        "status": PROVISIONAL if "far_share" in partial else factor_status("access"),
    },
    {
        "factor": "Caregiver capacity",
        "evidence": f"District context: {theme.fmt_int(row.pupils_per_teacher)} pupils per teacher, {pct('qualified_share')} of teachers qualified.",
        "level": level(row.capacity),
        "action": f"Recruit and train caregivers; assign the LEARN course '{COURSES['CAPACITY']}'.",
        "source": "MINEDUC yearbook 2024/25; LEARN progress",
        "status": factor_status("capacity"),
    },
    {
        "factor": "Child wellbeing",
        "evidence": f"District context: stunting {pct('stunting')} of children under 5.",
        "level": level(row.wellbeing),
        "action": f"Link with nutrition programmes; assign '{COURSES['NUTRITION']}'.",
        "source": "RDHS 2025",
        "status": factor_status("wellbeing"),
    },
    {
        "factor": "Water and sanitation",
        "evidence": f"{pct('water_share')} of households use improved water; {pct('sanitation_share')} improved sanitation.",
        "level": level(row.home),
        "action": f"Coordinate with WASH programmes near ECD centres; assign '{COURSES['WASH']}'.",
        "source": "Census 2022",
        "status": factor_status("home"),
    },
    {
        "factor": "Poverty",
        "evidence": f"Poverty rate {pct('poverty')} ({row.poverty_level} figure).",
        "level": level(row.poverty_score),
        "action": "Check fees and costs with parents; associated with lower attendance, not a proven cause.",
        "source": "EICV7 2023/24",
        "status": factor_status("poverty"),
    },
]
with theme.panel(
    "Evidence and recommended response",
    f"Bottleneck and actions: {status}; each row shows the status of its evidence",
    "clipboard",
):
    st.markdown(
        theme.table(
            evidence,
            [
                Col("factor", "Factor", strong=True),
                Col("evidence", "Evidence"),
                Col("level", "Level", fmt=lambda v, r: theme.pill(v)),
                Col("action", "Suggested action"),
                Col("source", "Source", fmt=lambda v, r: f"<span class='muted'>{escape(v)}</span>"),
                Col("status", "Status", fmt=lambda v, r: theme.badge(v)),
            ],
        ),
        unsafe_allow_html=True,
    )
    with st.expander(t("All indicators behind the factors")):
        keys = [k for k in LEVEL if k in row.index]
        st.markdown(
            theme.table(
                [
                    {
                        "indicator": LABELS[k],
                        "value": "–"
                        if pd.isna(row[k])
                        else (f"{row[k]:.2f}" if "log" in k or "per" in k else f"{row[k]:.0%}"),
                        "level": "district context" if LEVEL[k] == "district" else LEVEL[k],
                    }
                    for k in keys
                ],
                [
                    Col("indicator", "Indicator", strong=True),
                    Col("value", "Value", num=True),
                    Col("level", "Level"),
                ],
            ),
            unsafe_allow_html=True,
        )
