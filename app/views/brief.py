"""Screen 7. District brief: one printable page, every number cited; CSV and PDF exports."""

import pandas as pd
import streamlit as st

from irerero import brief
from irerero.config import (
    BOTTLENECK_COLOURS,
    COMPONENTS,
    DEFINITION,
    PRESETS,
    SIMULATED,
    STATUS_COLOURS,
    SUPPRESS_BELOW,
    TARGET_2029,
    TARGET_YEAR,
)
from irerero.learn import progress
from irerero.plan.frame import ranked
from irerero.track import forecast, plans
from irerero.ui import data, theme
from irerero.ui.roles import ANALYST, current

user = current()
eng = data.eng()
districts = data.districts()
if user.role == ANALYST:
    district_id = st.selectbox(
        "District", list(districts), format_func=districts.get, key="brief-d"
    )
else:
    district_id = user.district_id
name = districts[district_id]
target = data.target()
sectors = data.sectors()
frame = sectors[sectors.district_id == district_id]
simulated = (frame.status == SIMULATED).any()
status = SIMULATED if simulated else "model estimate"

theme.header(
    f"District brief · {name}",
    "One page for the district council. Use your browser's print, or download the PDF or CSV.",
    simulated=simulated,
)

preset = st.radio("Priority preset", list(PRESETS), index=2, horizontal=True)
weights = dict(zip(COMPONENTS, PRESETS[preset], strict=True))
result, used = ranked(frame, target, weights)
diag = data.diagnosis_now(target).set_index("geo_id")
result["bottleneck"] = result.geo_id.map(diag.bottleneck)
track = forecast.summary(data.table("forecast"), target).loc[district_id]

# --- page ---------------------------------------------------------------------------------
refs = {
    1: brief.SOURCE_ESTIMATE,
    2: brief.SOURCE_STANDARDS,
    3: brief.SOURCE_DISTANCE,
    4: brief.SOURCE_TREND,
    5: brief.SOURCE_DIAGNOSIS,
    6: f"Target: {TARGET_2029.citation}",
}
chip = theme.chip(track.status, STATUS_COLOURS[track.status])
st.markdown(
    f"#### Are we on track for {theme.fmt_pct(target)} by {TARGET_YEAR}? {chip}",
    unsafe_allow_html=True,
)
lines = [
    f"Children aged 3 to 5 in 2026: {theme.fmt_int(result.children_3_5.sum())} "
    f"(range {theme.fmt_int(result.low.sum())} to {theme.fmt_int(result.high.sum())}) [1]",
    f"Attending pre-primary in 2026: "
    f"{theme.fmt_pct(result.attending.sum() / result.children_3_5.sum())} [1]",
    f"Places needed to reach {theme.fmt_pct(target)}: {theme.fmt_int(result.places.sum())}, "
    f"or {theme.fmt_int(result.rooms.sum())} rooms and "
    f"{theme.fmt_int(result.caregivers_low.sum())}-{theme.fmt_int(result.caregivers_high.sum())} "
    "caregivers [2] [6]",
    f"Enrolment rate {theme.fmt_pct(track.latest, 1)} in 2024/25; projected "
    f"{theme.fmt_pct(track.projected, 1)} in {TARGET_YEAR} (80% range "
    f"{theme.fmt_pct(track.low)}-{theme.fmt_pct(track.high)}): {track.status} [4]",
]
for line in lines:
    st.markdown(f"- {line}  ·  {theme.badge(status)}", unsafe_allow_html=True)

st.markdown(f"**Top 5 sectors ({preset})** [1] [2] [3] [5]")
top = result.head(5)
table = pd.DataFrame(
    {
        "Rank": top["rank"],
        "Sector": top.name,
        "Children 3-5": top.children_3_5.round().astype(int),
        "Attending": (top.attendance_rate * 100).round().astype(int).astype(str) + "%",
        "Places": top.places,
        "Rooms": top.rooms,
        "> 1 km": (top.far_share * 100).round().astype(int).astype(str) + "%",
        "Bottleneck": top.bottleneck,
    }
)
st.dataframe(table, hide_index=True, use_container_width=True)
mix = result.bottleneck.value_counts()
st.markdown(
    "Bottlenecks across the district: "
    + " ".join(theme.chip(f"{k} {v}", BOTTLENECK_COLOURS[k]) for k, v in mix.items()),
    unsafe_allow_html=True,
)

plan_list = plans.plans(eng, district_id)
decisions = ""
if len(plan_list):
    items = plans.items(eng, int(plan_list.plan_id.iat[0]))
    counts = items.decision.value_counts()
    funded = items.status.value_counts()
    decisions = (
        f"Plan '{plan_list.name.iat[0]}': {counts.get('approved', 0)} approved, "
        f"{counts.get('edited', 0)} edited, {counts.get('rejected', 0)} rejected, "
        f"{counts.get('pending', 0)} pending; {funded.get('funded', 0)} funded, "
        f"{funded.get('done', 0)} done."
    )
    st.markdown(f"**Decisions.** {decisions}")
training = progress.summary(eng)
training = training[training.district_id == district_id]
training_line = ""
if len(training):
    req = training[training.required]
    training_line = (
        f"LEARN pilot: {req.completed.sum()} of {len(req)} required courses completed, "
        f"{req.overdue.sum()} overdue (simulated)."
    )
    st.markdown(f"**Training.** {training_line}")

st.markdown("**Sources**")
for n, text in refs.items():
    st.markdown(f"[{n}] {text}")
theme.note(
    f"{DEFINITION} Status of every number: {status}. Priority is relative to other sectors "
    "in the district. Associations, not causes. Decisions are made by people."
)

# --- exports ------------------------------------------------------------------------------
st.subheader("Export")
include = st.toggle(
    "Include simulated values (labelled SIMULATED)",
    value=False,
    help="Simulated values are left out of exports unless you include them here.",
)
long = pd.concat(
    [brief.district_rows(district_id, name, track, status), brief.sector_rows(result)],
    ignore_index=True,
)
exported = brief.export(long, include)
if exported.empty:
    st.warning(
        "Every value here is simulated, so the export is empty unless you include simulated "
        "values. Load the real files to export real figures."
    )
c1, c2 = st.columns(2)
c1.download_button(
    "Download CSV",
    brief.to_csv(long, include),
    file_name=f"irerero-brief-{name.lower()}.csv",
    mime="text/csv",
    disabled=exported.empty,
    icon=":material/table:",
)
pdf_table = table if (include or not simulated) else table.head(0)
pdf_lines = lines if (include or not simulated) else ["Values withheld: simulated."]
c2.download_button(
    "Download PDF",
    brief.pdf(
        f"District brief: {name}",
        [*pdf_lines, decisions, training_line],
        pdf_table,
        [f"[{n}] {t}" for n, t in refs.items()] + [DEFINITION],
        simulated=simulated and include,
    ),
    file_name=f"irerero-brief-{name.lower()}.pdf",
    mime="application/pdf",
    icon=":material/picture_as_pdf:",
)
theme.note(
    f"Counts of children under {SUPPRESS_BELOW} are exported as 'fewer than {SUPPRESS_BELOW}'. "
    "The CSV is long: one row per value, with its source, period and status."
)
