"""Screen 5. Caregiver home (LEARN): monthly check-in and My learning. Counts only, never
child names. A caregiver sees only their own centre and their own progress."""

from datetime import datetime

import pandas as pd
import streamlit as st

from irerero.config import SIMULATED
from irerero.learn import certificate, checkins, progress, triggers
from irerero.learn.checkins import CHALLENGES, LABELS, Checkin
from irerero.learn.simulate import LEARN_NOTE
from irerero.ui import data, theme
from irerero.ui.i18n import t
from irerero.ui.roles import current, demo_mode

user = current()
eng = data.eng()
centres = data.table("supply_extract").set_index("centre_id")
centre = centres.loc[user.centre_id]
sector_name = data.table("geo_unit").set_index("geo_id").name.get(centre.geo_id, "")
courses = data.table("course").set_index("course_id")
lessons = data.table("lesson")
quiz = data.table("quiz_item")


def bilingual(key: str) -> str:
    en, rw = LABELS[key]
    return f"{en} · {rw}"


theme.header(
    "Caregiver learning",
    t("{centre} · monthly check-in and your courses", centre=centre["name"]),
    simulated=centre.status == SIMULATED,
    crumbs=["Muhanga", f"{sector_name} sector", "Caregiver learning"],
    assistant="caregiver",
    hero=True,
)

history = checkins.frame(eng, [user.centre_id])
month = checkins.current_month()
last = history.iloc[-1] if len(history) else None
done = month in set(history.month)
mine = progress.assignments(eng, [user.user_id])
req = mine[mine.required_by.notna()]
k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi("This month's check-in", "Submitted" if done else "Due", "Your centre", month,
              "user input" if done else None, f"{len(history)} months recorded", "check" if done else "clock",
              "teal" if done else "gold")  # fmt: skip
with k2:
    theme.kpi("Attendance, last check-in", theme.fmt_pct(last.attendance_rate) if last is not None else "–",
              "Your centre's check-in", last.month if last is not None else None,
              last.status if last is not None else None,
              f"{theme.fmt_int(last.attendance_avg)} of {theme.fmt_int(last.enrolled)} children" if last is not None else None,
              "users", "blue")  # fmt: skip
with k3:
    theme.kpi("Required courses done", f"{int(req.completed_at.notna().sum())} of {len(req)}", "LEARN", "2026",
              None, "required on joining or by your officer", "book", "navy")  # fmt: skip
with k4:
    waiting = int((mine.status == "recommended").sum())
    theme.kpi("Suggested courses", str(waiting), "LEARN triggers", "2026", None,
              "waiting for your sector officer", "info", "purple")  # fmt: skip
check_col, learn_col = st.columns([3, 2])

# --- check-in -----------------------------------------------------------------------------
with (
    check_col,
    theme.panel(
        "Monthly check-in · Raporo y'ukwezi",
        f"{month} · counts only, never children's names · about two minutes"
        + (" · already submitted, you can correct it" if done else ""),
        "clipboard",
    ),
):
    with st.form("checkin", border=False):
        c1, c2 = st.columns(2)
        enrolled = c1.number_input(
            bilingual("enrolled"), 0, 500, int(last.enrolled) if last is not None else 0
        )
        present = c2.number_input(
            bilingual("attendance_avg"),
            0.0,
            500.0,
            float(last.attendance_avg) if last is not None else 0.0,
            step=1.0,
            format="%g",  # an average can be 25.5, but 31 shows as 31, not 31.00
        )
        carers_present = c1.number_input(
            bilingual("caregivers_present"),
            0,
            50,
            int(last.caregivers_present) if last is not None else 1,
        )
        meal_days = c2.slider(
            bilingual("meal_days_avg"),
            0.0,
            6.0,
            float(last.meal_days_avg) if last is not None else 5.0,
            0.5,
        )
        # Pre-filled from the last check-in, like the counts, so a correction keeps them.
        water = c1.radio(
            bilingual("water_available"),
            ["Yes · Yego", "No · Oya"],
            index=0 if last is None or bool(last.water_available) else 1,
            horizontal=True,
        )
        challenge = c2.selectbox(
            bilingual("main_challenge"),
            list(CHALLENGES),
            index=list(CHALLENGES).index(last.main_challenge)
            if last is not None and last.main_challenge in CHALLENGES
            else 0,
            format_func=lambda k: f"{CHALLENGES[k][0]} · {CHALLENGES[k][1]}",
        )
        sent = st.form_submit_button("Submit · Ohereza", type="primary")
    for i, message in enumerate(st.session_state.pop("checkin-saved", [])):
        (st.success if i == 0 else st.info)(message)
    if sent:
        entry = Checkin(
            centre_id=user.centre_id,
            month=month,
            enrolled=int(enrolled),
            attendance_avg=float(present),
            caregivers_present=int(carers_present),
            meal_days_avg=float(meal_days),
            water_available=water.startswith("Yes"),
            main_challenge=challenge,
        )
        try:
            checkins.submit(eng, user, entry)
            flagged = triggers.run(eng, data.diagnosis_now(data.target()))
            new_flags = [f for f in flagged if f[0] == user.user_id]
            # Rerun so the cards above show this month as submitted; the messages survive it.
            st.session_state["checkin-saved"] = [
                "Check-in saved. Murakoze!",
                *(
                    f"The course '{courses.at[course_id, 'title_en']}' is suggested for you. "
                    "Your sector officer will confirm it."
                    for _, course_id, _ in new_flags
                ),
            ]
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    with st.expander(t("Your centre's check-ins")):
        st.dataframe(
            pd.DataFrame(
                {
                    "Month": history.month,
                    "Enrolled": history.enrolled,
                    "Present (average)": history.attendance_avg,
                    "Attendance": (history.attendance_rate * 100).round(),
                    "Caregivers": history.caregivers_present,
                    "Meal days": history.meal_days_avg,
                    "Water": history.water_available.map({True: "yes", False: "no"}),
                    "Challenge": history.main_challenge.map(lambda k: CHALLENGES[k][0]),
                    "Status": history.status,
                }
            ).sort_values("Month", ascending=False),
            hide_index=True,
            width="stretch",
            column_config={"Attendance": st.column_config.NumberColumn(format="%d%%")},
        )

# --- learning -----------------------------------------------------------------------------
with learn_col, theme.panel("My learning · Amasomo yanjye", "Your courses and progress", "book"):
    theme.note(progress.QUIZ_NOTE + " Your quiz scores are visible only to you.")
    if mine.empty:
        st.markdown(theme.empty_state("No courses yet.", "book"), unsafe_allow_html=True)
    groups = [
        ("Required", mine[mine.status == "required"]),
        ("Suggested, waiting for your sector officer", mine[mine.status == "recommended"]),
        ("Completed", mine[mine.status == "completed"]),
    ]
    for title, rows in groups:
        if rows.empty:
            continue
        st.markdown(f"**{title}**")
        for a in rows.itertuples():
            course = courses.loc[a.course_id]
            n = int((lessons.course_id == a.course_id).sum())
            done_n = len(a.lessons_done or [])
            due = f" · due {a.due_date:%d %b %Y}" if pd.notna(a.due_date) else ""
            st.markdown(
                f"{theme.pill(a.status)} **{course.title_en}**<br><span class='ir-note'><i>{course.title_rw}</i>{due}</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(done_n / n, 1.0) if n else 0.0, text=f"{done_n} of {n} lessons")

with theme.panel("Course", "Lessons, quiz and certificate", "cap"):
    order = {"required": 0, "recommended": 1, "completed": 2}
    open_ids = mine[mine.status.isin(order)].sort_values("status", key=lambda s: s.map(order))
    if len(open_ids):
        pick = st.selectbox(
            t("Open a course"),
            open_ids.id.tolist(),
            format_func=lambda i: courses.at[
                open_ids.set_index("id").at[i, "course_id"], "title_en"
            ],
            key="course-pick",  # keeps the open course when a pass moves it to Completed
        )
        a = open_ids.set_index("id").loc[pick]
        course = courses.loc[a.course_id]
        st.subheader(f"{course.title_en} · {course.title_rw}")
        st.caption(f"Source: {course.source}")
        course_lessons = lessons[lessons.course_id == a.course_id].sort_values("position")
        for lesson in course_lessons.itertuples():
            ticked = lesson.position in (a.lessons_done or [])
            with st.expander(f"{'✓ ' if ticked else ''}Lesson {lesson.position}: {lesson.title}"):
                st.markdown(lesson.body_md)
                if not ticked and st.button(
                    t("Mark as done"), key=f"done-{pick}-{lesson.position}"
                ):
                    progress.mark_lesson(eng, user, int(pick), int(lesson.position))
                    st.rerun()
        if a.status == "recommended":
            st.info("You can read this course now; it becomes required once your officer confirms.")
        st.markdown("#### Quiz · five questions")
        items = quiz[quiz.course_id == a.course_id].sort_values("position")
        with st.form(f"quiz-{pick}"):
            answers = {}
            for q in items.itertuples():
                choice = st.radio(q.question, q.options, index=None, key=f"q-{pick}-{q.position}")
                answers[int(q.position)] = q.options.index(choice) if choice is not None else -1
            submitted = st.form_submit_button(t("Submit answers"))
            unanswered = sum(1 for chosen in answers.values() if chosen < 0)
            if submitted and unanswered:  # a blank answer is not a wrong one: ask, do not score
                st.warning(
                    f"Answer all {len(answers)} questions first: {unanswered} still to answer."
                )
            elif submitted:
                result = progress.submit_quiz(eng, user, int(pick), answers)
                # Re-read the course, so a pass shows the certificate straight away.
                a = progress.assignments(eng, [user.user_id]).set_index("id").loc[pick]
                if result["passed"]:
                    st.success(f"{result['correct']} of {result['total']}: course completed.")
                else:
                    st.warning(
                        f"{result['correct']} of {result['total']}. 4 of 5 completes the course; "
                        "read the lessons again and retry."
                    )
        if pd.notna(a.completed_at):
            st.download_button(
                t("Download certificate (PDF)"),
                certificate.pdf(
                    user.name,
                    str(centre["name"]),
                    str(course.title_en),
                    str(course.title_rw),
                    str(course.source),
                    pd.Timestamp(a.completed_at).to_pydatetime()
                    if pd.notna(a.completed_at)
                    else datetime.now(),
                    simulated=demo_mode(),
                ),
                file_name=f"certificate-{a.course_id}.pdf",
                mime="application/pdf",
                icon=":material/workspace_premium:",
            )
    theme.note(
        "Kinyarwanda labels and course titles are drafts awaiting review by a native speaker."
    )
    if centre.status == SIMULATED:
        theme.note(LEARN_NOTE)
