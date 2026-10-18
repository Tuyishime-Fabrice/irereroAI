"""Course assignments and progress.

Two courses are required on joining. The other two are flagged by triggers (a check-in with no
water or few meal days, or a sector WASH or stunting problem) and stay *recommended* until a
sector officer confirms them as required with a due date. Nothing becomes required
automatically. Every confirmation is logged.

Quiz scores are visible to the caregiver alone; officers and planners see aggregates only, and
never a ranking of caregivers. The quiz measures course knowledge, not teaching quality.
"""

from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from irerero import audit
from irerero.db.models import AppUser, Assignment, QuizItem
from irerero.learn.content import PASS_MARK
from irerero.roles import CAREGIVER, OFFICER, User

JOINING = ("ecd_standards", "safeguarding")
TRIGGERED = {
    "wash": ("checkin:no_water", "sector:WASH"),
    "nutrition": ("checkin:few_meals", "sector:STUNTING"),
}
MIN_FOR_AVERAGE = 3  # an average quiz score is shown only over at least three caregivers
QUIZ_NOTE = "Quiz measures course knowledge, not teaching quality."


def caregivers(eng: Engine) -> pd.DataFrame:
    with Session(eng) as s:
        rows = s.scalars(select(AppUser).where(AppUser.role == CAREGIVER))
        return pd.DataFrame(
            [
                {
                    "caregiver_id": u.user_id,
                    "name": u.name,
                    "centre_id": u.centre_id,
                    "sector_id": u.sector_id,
                    "district_id": u.district_id,
                }
                for u in rows
            ],
            columns=["caregiver_id", "name", "centre_id", "sector_id", "district_id"],
        )


def assignments(eng: Engine, caregiver_ids: list[str] | None = None) -> pd.DataFrame:
    query = select(Assignment)
    if caregiver_ids is not None:
        query = query.where(Assignment.caregiver_id.in_(caregiver_ids))
    columns = [c.name for c in Assignment.__table__.columns]
    with Session(eng) as s:
        rows = [{c: getattr(r, c) for c in columns} for r in s.scalars(query)]
    return pd.DataFrame(rows, columns=columns)


def recommend(eng: Engine, caregiver_id: str, course_id: str, trigger: str) -> bool:
    """Flag a course for a caregiver as recommended. Returns True if a new flag was added."""
    with Session(eng) as s:
        exists = s.scalars(
            select(Assignment).where(
                Assignment.caregiver_id == caregiver_id, Assignment.course_id == course_id
            )
        ).first()
        if exists is not None:
            return False
        s.add(
            Assignment(
                caregiver_id=caregiver_id,
                course_id=course_id,
                trigger=trigger,
                required_by=None,
                lessons_done=[],
                status="recommended",
            )
        )
        s.commit()
        return True


def _officer_can(s: Session, officer: User, caregiver_id: str) -> None:
    carer = s.get(AppUser, caregiver_id)
    if officer.role != OFFICER or carer is None or carer.sector_id != officer.sector_id:
        raise PermissionError("only the sector officer of the caregiver's sector can do this")


def confirm(
    eng: Engine, officer: User, assignment_id: int, due: date, reason: str | None = None
) -> None:
    with Session(eng) as s:
        a = s.get(Assignment, assignment_id)
        if a is None:
            raise KeyError(assignment_id)
        _officer_can(s, officer, a.caregiver_id)
        if a.status != "recommended":
            raise ValueError("only a recommended course can be confirmed")
        before = {"status": a.status, "required_by": a.required_by}
        a.required_by = "officer"
        a.confirmed_by = officer.user_id
        a.due_date = due
        a.status = "required"
        audit.write(
            s,
            officer,
            "assignment.confirm",
            "assignment",
            a.id,
            before=before,
            after={
                "status": a.status,
                "course_id": a.course_id,
                "caregiver_id": a.caregiver_id,
                "due_date": due.isoformat(),
                "trigger": a.trigger,
            },
            reason=(reason or "").strip() or None,
        )
        s.commit()


def dismiss(eng: Engine, officer: User, assignment_id: int, reason: str) -> None:
    if not (reason or "").strip():
        raise ValueError("a reason is required to set a flag aside")
    with Session(eng) as s:
        a = s.get(Assignment, assignment_id)
        if a is None:
            raise KeyError(assignment_id)
        _officer_can(s, officer, a.caregiver_id)
        if a.status != "recommended":
            raise ValueError("only a recommended course can be set aside")
        a.status = "set aside"
        audit.write(
            s,
            officer,
            "assignment.dismiss",
            "assignment",
            a.id,
            before={"status": "recommended"},
            after={"status": a.status},
            reason=reason.strip(),
        )
        s.commit()


def _own(s: Session, user: User, assignment_id: int) -> Assignment:
    a = s.get(Assignment, assignment_id)
    if a is None or a.caregiver_id != user.user_id:
        raise PermissionError("caregivers see and change only their own courses")
    return a


def mark_lesson(eng: Engine, user: User, assignment_id: int, position: int) -> None:
    with Session(eng) as s:
        a = _own(s, user, assignment_id)
        done = sorted(set(a.lessons_done or []) | {int(position)})
        a.lessons_done = done
        s.commit()


def submit_quiz(
    eng: Engine, user: User, assignment_id: int, answers: dict[int, int]
) -> dict[str, Any]:
    """answers: question position -> chosen option. Passing (4 of 5) completes the course."""
    with Session(eng) as s:
        a = _own(s, user, assignment_id)
        items = s.scalars(select(QuizItem).where(QuizItem.course_id == a.course_id)).all()
        correct = sum(1 for q in items if answers.get(q.position) == q.answer)
        score = correct / len(items)
        a.score = max(score, a.score or 0.0)
        passed = score >= PASS_MARK
        if passed and a.completed_at is None:
            a.completed_at = audit.now()
            a.status = "completed"
        s.commit()
        return {"correct": correct, "total": len(items), "score": score, "passed": passed}


def overdue(frame: pd.DataFrame, today: date | None = None) -> pd.Series:
    today = today or date.today()
    due = pd.to_datetime(frame.due_date).dt.date
    return frame.completed_at.isna() & frame.required_by.notna() & due.notna() & (due < today)


def summary(eng: Engine, today: date | None = None) -> pd.DataFrame:
    """One row per assignment with caregiver, centre, sector and district, and flags."""
    carers = caregivers(eng)
    a = assignments(eng, carers.caregiver_id.tolist())
    out = a.merge(carers, on="caregiver_id", how="left")
    out["required"] = out.required_by.notna()
    out["completed"] = out.completed_at.notna()
    out["overdue"] = overdue(out, today) if len(out) else pd.Series(dtype=bool)
    return out


def completion_by_district(eng: Engine) -> dict[str, float]:
    """Share of caregivers who completed every required course, per district."""
    s = summary(eng)
    required = s[s.required]
    if required.empty:
        return {}
    per_carer = required.groupby(["district_id", "caregiver_id"]).completed.all()
    return per_carer.groupby(level=0).mean().round(3).to_dict()


def aggregate(frame: pd.DataFrame, by: str) -> pd.DataFrame:
    """Required, completed, overdue and average score by centre or sector. Scores are averaged
    only over at least MIN_FOR_AVERAGE caregivers."""
    req = frame[frame.required]
    if req.empty:
        return pd.DataFrame(
            columns=[
                by,
                "caregivers",
                "required",
                "completed",
                "overdue",
                "share_completed",
                "average_score",
            ]
        )
    g = req.groupby(by)
    out = pd.DataFrame(
        {
            "caregivers": g.caregiver_id.nunique(),
            "required": g.size(),
            "completed": g.completed.sum(),
            "overdue": g.overdue.sum(),
        }
    )
    out["share_completed"] = out.completed / out.required
    scored = frame[frame.score.notna()].groupby(by)
    avg = scored.score.mean()
    n = scored.caregiver_id.nunique()
    out["average_score"] = avg.where(n >= MIN_FOR_AVERAGE)
    return out.reset_index()


def default_due(today: date | None = None, days: int = 30) -> date:
    return (today or date.today()) + timedelta(days=days)
