"""Screen 3. Sector profile (DIAGNOSE): what is holding pre-primary attendance back here."""

import altair as alt
import pandas as pd
import streamlit as st

from irerero.config import BOTTLENECK_COLOURS, GREEN, MUTED, NAVY, SIMULATED
from irerero.diagnose.features import LABELS, LEVEL
from irerero.diagnose.peer import MODEL_LABELS
from irerero.diagnose.rules import FACTOR_LABELS, FACTOR_LEVEL, FACTORS
from irerero.ui import data, theme
from irerero.ui.roles import ANALYST, OFFICER, current

user = current()
target = data.target()
diag = data.diagnosis_now(target)
districts = data.districts()

if user.role == OFFICER:
    geo_id = user.sector_id
    district_id = user.district_id
else:
    if user.role == ANALYST:
        district_id = st.selectbox(
            "District", list(districts), format_func=districts.get, key="sector-district"
        )
    else:
        district_id = user.district_id
    options = diag[diag.district_id == district_id].sort_values("name")
    preselect = st.session_state.get("sector_id")
    ids = options.geo_id.tolist()
    geo_id = st.selectbox(
        "Sector",
        ids,
        index=ids.index(preselect) if preselect in ids else 0,
        format_func=dict(zip(options.geo_id, options.name, strict=True)).get,
    )
st.session_state["sector_id"] = geo_id
row = diag.set_index("geo_id").loc[geo_id]
peers = diag[diag.district_id == district_id]
simulated = row.status == SIMULATED
status = SIMULATED if simulated else "model estimate"
run = data.table("model_run")
chosen = run[run.chosen].iloc[0] if len(run) else None
fallback = bool(row.fallback)

theme.header(
    f"Sector profile · {row['name']}",
    f"{districts[district_id]} district · diagnosis at a target of {theme.fmt_pct(target)}",
    simulated=simulated,
)

colour = BOTTLENECK_COLOURS[row.bottleneck]
st.markdown(f"#### Main bottleneck {theme.chip(row.bottleneck, colour)}", unsafe_allow_html=True)
st.markdown(f"**Suggested intervention.** {row.intervention}")
for reason in row.reasons:
    st.markdown(f"- {reason}")
theme.note(
    "Rules, not a model: the first rule that applies sets the main bottleneck. A person "
    "decides what goes into the plan."
)

c1, c2, c3 = st.columns(3)
with c1:
    theme.card(
        "Children aged 3 to 5 (2026)",
        theme.fmt_int(row.children_3_5),
        "IrereroAI 2026 estimate",
        "2026",
        status,
        f"range {theme.fmt_int(row.children_low)} to {theme.fmt_int(row.children_high)}",
    )
with c2:
    theme.card(
        "Attending pre-primary (2026)",
        theme.fmt_pct(row.attendance_rate),
        "IrereroAI 2026 estimate",
        "2026",
        status,
        f"census 2022: {theme.fmt_pct(row.attendance_2022)}",
    )
with c3:
    theme.card(
        "Children more than 1 km from a school",
        theme.fmt_pct(row.far_share),
        "IrereroAI distance layer",
        "2026",
        status,
    )

left, right = st.columns(2)
with left:
    st.subheader("Five factors")
    factor_rows = pd.DataFrame(
        {
            "factor": [FACTOR_LABELS[f] for f in FACTORS],
            "score": [row["poverty_score"] if f == "poverty" else row[f] for f in FACTORS],
            "level": [
                f"{FACTOR_LEVEL[f]}"
                if f != "poverty"
                else ("sector" if row.poverty_level == "sector" else "district context")
                for f in FACTORS
            ],
        }
    )
    factor_rows["text"] = [
        "no data" if pd.isna(s) else f"{s:.2f} · {lvl}"
        for s, lvl in zip(factor_rows.score, factor_rows.level, strict=True)
    ]
    base = alt.Chart(factor_rows).encode(
        y=alt.Y("factor:N", sort=None, title=None),
        x=alt.X("score:Q", scale=alt.Scale(domain=[0, 1]), title="National percentile (1 = worst)"),
    )
    bars = base.mark_bar(size=22).encode(
        color=alt.Color(
            "level:N",
            scale=alt.Scale(domain=["sector", "district context"], range=[NAVY, "#8FA8C0"]),
            legend=alt.Legend(title=None, orient="bottom"),
        ),
        tooltip=["factor", alt.Tooltip("score:Q", format=".2f"), "level"],
    )
    labels = base.mark_text(align="left", dx=4, color=MUTED, fontSize=11).encode(text="text")
    rule = (
        alt.Chart(pd.DataFrame({"x": [0.75]}))
        .mark_rule(strokeDash=[4, 3], color=MUTED)
        .encode(x="x:Q")
    )
    st.altair_chart((bars + labels + rule).properties(height=240), use_container_width=True)
    theme.note(
        "Dashed line: worst quarter nationally. District context applies to every sector of "
        "the district and is not a sector value."
    )

with right:
    st.subheader("Observed vs expected attendance")
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
    interval = base.mark_rule(strokeWidth=6, opacity=0.35, color=GREEN).encode(
        x=alt.X("low:Q", axis=alt.Axis(format="%"), title="Attendance, census 2022"),
        x2="high:Q",
    )
    expected = base.mark_tick(color=GREEN, thickness=2, size=14).encode(x="expected:Q")
    observed = base.mark_point(filled=True, size=70).encode(
        x="observed:Q",
        color=alt.condition(alt.datum.selected, alt.value("#D55E00"), alt.value(NAVY)),
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
        (interval + expected + observed).properties(height=max(220, 30 * len(chart))),
        use_container_width=True,
    )
    model_name = MODEL_LABELS.get(chosen.model_id, "") if chosen is not None else ""
    theme.note(
        f"Dot: observed (this sector as an orange diamond). Bar: 80% interval of the expected "
        f"value from {('the district average' if fallback else model_name)}, fitted without the "
        "sector's own district. Status: " + status + "."
    )

    st.markdown(
        f"**{row['name']}:** observed {theme.fmt_pct(row.observed)}, expected "
        f"{theme.fmt_pct(row.expected)} (80% interval {theme.fmt_pct(row.low)} to "
        f"{theme.fmt_pct(row.high)})."
    )
    if not fallback and isinstance(row.drivers, list) and row.drivers:
        st.markdown("**Top 3 drivers of the expected value** · associated with, not caused by")
        for d in row.drivers:
            sign = "raises" if d["contribution_pp"] >= 0 else "lowers"
            st.markdown(
                f"- {d['label']}: {sign} the expectation by {abs(d['contribution_pp']):.1f} "
                "points compared with an average sector"
            )

st.subheader("Indicators behind the factors")
names = [k for k in LEVEL if k in row.index]
st.dataframe(
    pd.DataFrame(
        {
            "Indicator": [LABELS[k] for k in names],
            "Value": [
                "–"
                if pd.isna(row[k])
                else (f"{row[k]:.2f}" if "log" in k or "per" in k else f"{row[k]:.0%}")
                for k in names
            ],
            "Level": ["district context" if LEVEL[k] == "district" else LEVEL[k] for k in names],
            "Status": status,
        }
    ),
    hide_index=True,
    use_container_width=True,
    height=38 + 35 * len(names),
)
if user.can_decide:
    st.session_state.setdefault("plan_basket", [])
    if st.button("Add to plan", type="primary", icon=":material/add:"):
        if geo_id not in st.session_state["plan_basket"]:
            st.session_state["plan_basket"].append(geo_id)
        st.success(f"{row['name']} added. Open Plan builder to review and decide.")
