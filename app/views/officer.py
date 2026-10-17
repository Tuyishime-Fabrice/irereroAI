"""Screen 6. Officer training view (LEARN): confirm flagged courses, follow up overdue training,
see check-in problems. Aggregates only: no ranking of caregivers, no individual quiz scores."""

import pandas as pd
import streamlit as st

from irerero.learn import checkins, progress
from irerero.learn.checkins import CHALLENGES
from irerero.ui import data, theme
from irerero.ui.roles import current

user = current()
eng = data.eng()
units = data.table("geo_unit").set_index("geo_id")
courses = data.table("course").set_index("course_id")
sector_name = units.name.get(user.sector_id, user.sector_id)
summary = progress.summary(eng)
mine = summary[summary.sector_id == user.sector_id]
centres = data.table("supply_extract").set_index("centre_id")

theme.header(
    f"Training · {sector_name} sector",
    "Confirm suggested courses, follow up overdue training and centre check-ins.",
    simulated=True,
)
TRIGGER_TEXT = {
    "checkin:no_water": "latest check-in: no water or handwashing",
    "checkin:few_meals": "latest check-in: meals on fewer than 3 days a week",
    "sector:WASH": "sector: water and sanitation among the weakest quarter",
    "sector:STUNTING": "district: stunting among the highest quarter",
}

# --- flags --------------------------------------------------------------------------------
st.subheader("Suggested courses to confirm")
flags = mine[mine.status == "recommended"].sort_values(["centre_id", "course_id"])
if flags.empty:
    st.success("Nothing waiting for confirmation.")
for f in flags.itertuples():
    centre = centres.name.get(f.centre_id, f.centre_id)
    course = courses.loc[f.course_id]
    with st.container(border=True):
        st.markdown(
            f"**{course.title_en}** · *{course.title_rw}* · caregiver at {centre}  \n"
            f"Why: {TRIGGER_TEXT.get(f.trigger, f.trigger)}"
        )
        c1, c2, c3 = st.columns([1, 2, 1])
        due = c1.date_input("Due date", progress.default_due(), key=f"due-{f.id}")
        reason = c2.text_input("Note (required to set aside)", key=f"why-{f.id}")
        if c3.button("Confirm as required", key=f"ok-{f.id}", type="primary"):
            progress.confirm(eng, user, int(f.id), due, reason)
            data.clear()
            st.rerun()
        if c3.button("Set aside", key=f"no-{f.id}"):
            try:
                progress.dismiss(eng, user, int(f.id), reason)
                data.clear()
                st.rerun()
            except ValueError as error:
                st.error(str(error))
theme.note(
    "Nothing becomes required automatically: each confirmation is recorded in the audit log."
)

# --- check-ins ----------------------------------------------------------------------------
st.subheader("Latest check-ins")
sector_centres = centres[centres.geo_id == user.sector_id].index.tolist()
latest = checkins.problems(checkins.frame(eng, sector_centres))
if latest.empty:
    st.info("No check-ins yet.")
else:
    flags_text = []
    for r in latest.itertuples():
        parts = []
        if r.no_water:
            parts.append("no water or handwashing")
        if r.few_meals:
            parts.append(f"meals on {r.meal_days_avg:g} days a week")
        if r.attendance_drop:
            parts.append(
                f"attendance down to {r.attendance_rate:.0%} from about {r.previous_rate:.0%}"
            )
        flags_text.append("; ".join(parts) or "–")
    st.dataframe(
        pd.DataFrame(
            {
                "Centre": [centres.name.get(c, c) for c in latest.centre_id],
                "Month": latest.month,
                "Enrolled": latest.enrolled,
                "Attendance": (latest.attendance_rate * 100).round(),
                "Meal days": latest.meal_days_avg,
                "Water": latest.water_available.map({True: "yes", False: "no"}),
                "Challenge": latest.main_challenge.map(lambda k: CHALLENGES[k][0]),
                "Needs follow-up": flags_text,
                "Status": latest.status,
            }
        ),
        hide_index=True,
        use_container_width=True,
        column_config={"Attendance": st.column_config.NumberColumn(format="%d%%")},
    )

# --- completion ---------------------------------------------------------------------------
st.subheader("Required training by centre")
by_centre = progress.aggregate(mine, "centre_id")
if len(by_centre):
    st.dataframe(
        pd.DataFrame(
            {
                "Centre": [centres.name.get(c, c) for c in by_centre.centre_id],
                "Caregivers": by_centre.caregivers,
                "Required courses": by_centre.required,
                "Completed": by_centre.completed,
                "Overdue": by_centre.overdue,
                "Completed (%)": (by_centre.share_completed * 100).round(),
            }
        ).sort_values("Centre"),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Completed (%)": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%d%%"
            )
        },
    )
over = mine[mine.overdue]
st.markdown(f"**Overdue, to follow up ({len(over)})**")
if len(over):
    st.dataframe(
        pd.DataFrame(
            {
                "Caregiver": over.name,
                "Centre": [centres.name.get(c, c) for c in over.centre_id],
                "Course": [courses.at[c, "title_en"] for c in over.course_id],
                "Due": over.due_date,
            }
        ).sort_values(["Centre", "Course"]),
        hide_index=True,
        use_container_width=True,
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
