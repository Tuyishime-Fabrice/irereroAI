"""Screen 6. Caregiver learning, officer view (LEARN): confirm flagged courses, follow up overdue
training, see check-in problems. Aggregates only: no ranking of caregivers, no individual quiz
scores."""

from html import escape

import streamlit as st

from irerero.learn import checkins, progress
from irerero.learn.checkins import CHALLENGES
from irerero.learn.simulate import LEARN_NOTE
from irerero.ui import data, theme
from irerero.ui.i18n import t
from irerero.ui.roles import current
from irerero.ui.theme import Col

user = current()
eng = data.eng()
units = data.table("geo_unit").set_index("geo_id")
courses = data.table("course").set_index("course_id")
sector_name = units.name.get(user.sector_id, user.sector_id)
summary = progress.summary(eng)
mine = summary[summary.sector_id == user.sector_id]
centres = data.table("supply_extract").set_index("centre_id")
# LEARN centres are those with caregiver accounts; other mapped services are not in the pilot.
pilot = set(progress.caregivers(eng).centre_id.dropna())
sector_centres = centres[
    (centres.geo_id == user.sector_id) & centres.index.isin(pilot)
].index.tolist()
latest = checkins.problems(checkins.frame(eng, sector_centres))

theme.header(
    "Caregiver learning",
    t(
        "{sector} sector · confirm suggested courses, follow up training and centre check-ins.",
        sector=sector_name,
    ),
    simulated=True,
    crumbs=["Muhanga", f"{sector_name} sector", "Caregiver learning"],
    assistant="officer",
    hero=True,
)
TRIGGER_TEXT = {
    "checkin:no_water": "latest check-in: no water or handwashing",
    "checkin:few_meals": "latest check-in: meals on fewer than 3 days a week",
    "sector:WASH": "sector: water and sanitation among the weakest quarter",
    "sector:STUNTING": "district: stunting among the highest quarter",
}

flags = mine[mine.status == "recommended"].sort_values(["centre_id", "course_id"])
req = mine[mine.required]
followups = (
    int((latest.no_water | latest.few_meals | latest.attendance_drop).sum()) if len(latest) else 0
)
k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi("Waiting for your confirmation", str(len(flags)), "LEARN triggers", "2026", None,
              "suggested courses", "clipboard", "gold")  # fmt: skip
with k2:
    theme.kpi("Centres to follow up", str(followups), "Latest check-ins", latest.month.max() if len(latest) else None,
              "simulated", f"of {len(sector_centres)} centres", "alert", "rose")  # fmt: skip
with k3:
    theme.kpi("Required training completed", theme.fmt_pct(req.completed.mean()) if len(req) else "–",
              "LEARN progress", "2026", "simulated", f"{int(req.completed.sum())} of {len(req)} courses",
              "cap", "teal")  # fmt: skip
with k4:
    theme.kpi("Overdue courses", str(int(mine.overdue.sum())), "LEARN progress", "2026", "simulated",
              "to follow up with caregivers", "clock", "purple")  # fmt: skip

left, right = st.columns([1, 1])
# --- flags --------------------------------------------------------------------------------
with (
    left,
    theme.panel(
        "Suggested courses to confirm", "Nothing becomes required automatically.", "clipboard"
    ),
):
    if flags.empty:
        st.markdown(
            theme.empty_state("Nothing waiting for confirmation.", "check"), unsafe_allow_html=True
        )
    for f in flags.itertuples():
        centre = centres.name.get(f.centre_id, f.centre_id)
        course = courses.loc[f.course_id]
        with st.container(key=f"ir-flag-{f.id}"):
            st.markdown(
                f"{theme.pill('recommended')} **{escape(course.title_en)}** · <i>{escape(course.title_rw)}</i><br>"
                f"<span class='ir-note'>Caregiver at {escape(centre)} · why: "
                f"{escape(TRIGGER_TEXT.get(f.trigger, f.trigger))}</span>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 2])
            due = c1.date_input(t("Due date"), progress.default_due(), key=f"due-{f.id}")
            reason = c2.text_input(t("Note (required to set aside)"), key=f"why-{f.id}")
            b1, b2 = st.columns(2)
            if b1.button(
                t("Confirm as required"), key=f"ok-{f.id}", type="primary", width="stretch"
            ):
                progress.confirm(eng, user, int(f.id), due, reason)
                data.clear()
                st.rerun()
            if b2.button(t("Set aside"), key=f"no-{f.id}", width="stretch"):
                try:
                    progress.dismiss(eng, user, int(f.id), reason)
                    data.clear()
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    theme.note("Each confirmation and set-aside is recorded in the audit log.")

# --- completion ---------------------------------------------------------------------------
with right, theme.panel("Required training by centre", "Completion, not scores", "cap"):
    by_centre = progress.aggregate(mine, "centre_id")
    by_centre["centre"] = [centres.name.get(c, c) for c in by_centre.centre_id]
    st.markdown(
        theme.table(
            by_centre.sort_values("centre").to_dict(orient="records"),
            [
                Col("centre", "Centre", strong=True),
                Col("required", "Required", num=True),
                Col("completed", "Completed", num=True),
                Col("overdue", "Overdue", num=True),
                Col("share_completed", "Done", fmt=lambda v, r: theme.fmt_pct(v), num=True),
            ],
            empty="No required courses yet.",
        ),
        unsafe_allow_html=True,
    )
    sector_agg = progress.aggregate(mine, "sector_id")
    avg = sector_agg.average_score.iat[0] if len(sector_agg) else None
    st.markdown(
        "**Average quiz score in the sector:** "
        + (
            f"{avg:.0%}"
            if avg is not None and avg == avg
            else f"not shown (fewer than {progress.MIN_FOR_AVERAGE} caregivers with a score)"
        )
    )
    theme.note(progress.QUIZ_NOTE + " Caregivers are never ranked; individual scores stay private.")

with right, theme.panel("Overdue, to follow up", "Required courses past their due date", "clock"):
    over = mine[mine.overdue]
    st.markdown(
        theme.table(
            [
                {
                    "centre": centres.name.get(r.centre_id, r.centre_id),
                    "course": courses.at[r.course_id, "title_en"],
                    "due": f"{r.due_date:%d %b %Y}",
                }
                for r in over.sort_values(["centre_id", "course_id"]).itertuples()
            ],
            [Col("centre", "Centre", strong=True), Col("course", "Course"), Col("due", "Due")],
            empty="Nothing overdue.",
        ),
        unsafe_allow_html=True,
    )

# --- check-ins ----------------------------------------------------------------------------
with theme.panel("Latest check-ins", "One row per centre · counts only", "home"):
    if latest.empty:
        st.markdown(theme.empty_state("No check-ins yet."), unsafe_allow_html=True)
    else:
        rows = []
        for r in latest.itertuples():
            parts = []
            if r.no_water:
                parts.append(theme.pill("High", "No water"))
            if r.few_meals:
                parts.append(theme.pill("Medium", f"Meals {r.meal_days_avg:g} days"))
            if r.attendance_drop:
                parts.append(
                    theme.pill(
                        "Medium", f"Attendance {r.attendance_rate:.0%} (was ~{r.previous_rate:.0%})"
                    )
                )
            rows.append(
                {
                    "centre": centres.name.get(r.centre_id, r.centre_id),
                    "month": r.month,
                    "attendance": theme.fmt_pct(r.attendance_rate),
                    "challenge": CHALLENGES[r.main_challenge][0],
                    "follow": " ".join(parts) or "<span class='muted'>–</span>",
                }
            )
        st.markdown(
            theme.table(
                rows,
                [
                    Col("centre", "Centre", strong=True),
                    Col("month", "Month"),
                    Col("attendance", "Attendance", num=True),
                    Col("challenge", "Challenge"),
                    Col("follow", "Needs follow-up", fmt=lambda v, r: v),
                ],
            ),
            unsafe_allow_html=True,
        )
        theme.note(LEARN_NOTE)
