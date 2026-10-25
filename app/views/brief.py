"""Screen 7. District brief: one printable page, every number cited; CSV and PDF exports."""

from html import escape

import pandas as pd
import streamlit as st

from irerero import brief
from irerero.config import (
    COMPONENTS,
    DEFINITION,
    PRESETS,
    SIMULATED,
    SUPPRESS_BELOW,
    TARGET_2029,
    TARGET_YEAR,
)
from irerero.learn import progress
from irerero.plan.frame import distance_status, ranked, status_of
from irerero.track import forecast, plans
from irerero.ui import data, theme
from irerero.ui.roles import ANALYST, current

user = current()
eng = data.eng()
districts = data.districts()
district_id = (
    st.session_state.get("brief-d", next(iter(districts)))
    if user.role == ANALYST
    else user.district_id
)
name = districts[district_id]
target = data.target()
sectors = data.sectors()
frame = sectors[sectors.district_id == district_id]
forecast_rows = data.table("forecast")
diagnosed = data.diagnosis_now(target)
# each part has its own status: the estimate, the ranking (with the peer gap), the distance
# layer, the trend and the bottleneck rules become real at different times
status = status_of(frame)
rank_status = SIMULATED if SIMULATED in (status, *frame.peer_status.dropna().unique()) else status
far_status = distance_status(frame)
track_status = status_of(forecast_rows[forecast_rows.geo_id == district_id])
diag_status = status_of(diagnosed[diagnosed.district_id == district_id])
simulated = SIMULATED in (status, rank_status, far_status, track_status, diag_status)

theme.header(
    "District brief",
    "One page for the district council. Use your browser's print, or download the PDF or CSV.",
    simulated=simulated,
    crumbs=["Rwanda", frame.province.iat[0] if len(frame) else "", name, "District brief"],
    assistant="brief",
)

with theme.panel(key="filters"):
    f1, f2 = st.columns([1, 2])
    if user.role == ANALYST:
        f1.selectbox("District", list(districts), format_func=districts.get, key="brief-d")
    else:
        f1.selectbox("District", [district_id], format_func=districts.get, disabled=True)
    preset = f2.radio("Priority preset", list(PRESETS), index=2, horizontal=True)
weights = dict(zip(COMPONENTS, PRESETS[preset], strict=True))
result, used = ranked(frame, target, weights)
diag = diagnosed.set_index("geo_id")
result["bottleneck"] = result.geo_id.map(diag.bottleneck)
result["rank_status"], result["far_status"] = rank_status, far_status
result["bottleneck_status"] = result.geo_id.map(diag.status)
track = forecast.summary(forecast_rows, target).loc[district_id]

# --- page ---------------------------------------------------------------------------------
refs = {
    1: brief.SOURCE_ESTIMATE,
    2: brief.SOURCE_STANDARDS,
    3: brief.SOURCE_DISTANCE,
    4: brief.SOURCE_TREND,
    5: brief.SOURCE_DIAGNOSIS,
    6: f"Target: {TARGET_2029.citation}",
}
with theme.panel(
    f"{name} district · pre-primary brief",
    f"Target {theme.fmt_pct(target)} by {TARGET_YEAR} · each figure shows its status",
    "book",
):
    st.markdown(
        f"#### Are we on track for {theme.fmt_pct(target)} by {TARGET_YEAR}? {theme.pill(track.status)}",
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
    line_status = [status, status, status, track_status]
    st.markdown(
        '<ul class="ir-list">'
        + "".join(
            f"<li>{escape(line)} {theme.badge(s)}</li>"
            for line, s in zip(lines, line_status, strict=True)
        )
        + "</ul>",
        unsafe_allow_html=True,
    )

    st.markdown(f"**Top 5 sectors ({preset})** [1] [2] [3] [5]")
    top = result.head(5)
    table = pd.DataFrame(  # the PDF table: counts of children suppressed as in the CSV
        {
            "Rank": top["rank"],
            "Sector": top.name,
            "Children 3-5": brief.suppress_counts(top.children_3_5.round().astype(int)),
            "Attending": (top.attendance_rate * 100).round().astype(int).astype(str) + "%",
            "Places": brief.suppress_counts(top.places),
            "Rooms": top.rooms,
            "> 1 km": (top.far_share * 100).round().astype(int).astype(str) + "%",
            "Bottleneck": top.bottleneck,
        }
    )
    st.markdown(
        theme.table(
            top.to_dict(orient="records"),
            [
                theme.Col("rank", "Rank", num=True),
                theme.Col("name", "Sector", strong=True),
                theme.Col(
                    "children_3_5", "Children 3–5", fmt=lambda v, r: theme.fmt_int(v), num=True
                ),
                theme.Col(
                    "attendance_rate", "Attending", fmt=lambda v, r: theme.fmt_pct(v), num=True
                ),
                theme.Col("places", "Places", fmt=lambda v, r: theme.fmt_int(v), num=True),
                theme.Col("rooms", "Rooms", fmt=lambda v, r: theme.fmt_int(v), num=True),
                theme.Col("far_share", "> 1 km", fmt=lambda v, r: theme.fmt_pct(v), num=True),
                theme.Col("bottleneck", "Bottleneck", fmt=lambda v, r: theme.pill(v)),
            ],
        ),
        unsafe_allow_html=True,
    )
    mix = result.bottleneck.value_counts()
    st.markdown(
        "Bottlenecks across the district: "
        + " ".join(theme.pill(k, f"{theme.PILLS[k][1]} {v}") for k, v in mix.items()),
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

    st.markdown(
        '<div class="ir-sub">Sources</div><ol class="ir-sources">'
        + "".join(f"<li>[{n}] {escape(text)}</li>" for n, text in refs.items())
        + "</ol>",
        unsafe_allow_html=True,
    )
    theme.note(
        f"{DEFINITION} Children, places and rooms: {status}; ranking: {rank_status}; > 1 km: "
        f"{far_status}; trend: {track_status}; bottlenecks: {diag_status}. Priority is relative "
        "to other sectors in the district. Associations, not causes. Decisions are made by "
        "people."
    )


# --- exports ------------------------------------------------------------------------------
with theme.panel(
    "Export", "Simulated values are left out unless you include them, then labelled.", "database"
):
    include = st.toggle(
        "Include simulated values (labelled SIMULATED)",
        value=False,
        help="Simulated values are left out of exports unless you include them here.",
    )
    long = pd.concat(
        [brief.district_rows(district_id, name, track, track_status), brief.sector_rows(result)],
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
    # without simulated values, the PDF keeps the real lines and columns only
    pdf_lines = [
        line for line, s in zip(lines, line_status, strict=True) if include or s != SIMULATED
    ]
    hidden = [] if include else [
        column for column, s in (("Rank", rank_status), ("> 1 km", far_status),
                                 ("Bottleneck", diag_status)) if s == SIMULATED
    ]  # fmt: skip
    pdf_table = table.drop(columns=hidden) if status != SIMULATED or include else table.head(0)
    if hidden:
        pdf_lines.append(f"Withheld as simulated: {', '.join(hidden)}.")
    c2.download_button(
        "Download PDF",
        brief.pdf(
            f"District brief: {name}",
            # LEARN figures are simulated pilot data: only with simulated values included.
            [*pdf_lines, decisions, *([training_line] if include else [])],
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
