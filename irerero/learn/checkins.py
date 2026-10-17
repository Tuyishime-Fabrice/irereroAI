"""Monthly centre check-in: counts only, never child names, under two minutes.

enrolled             children enrolled this month
attendance_avg       children present on an average day
caregivers_present   caregivers present on an average day
meal_days_avg        days a week a meal was served, averaged over the month (0 to 6)
water_available      water and handwashing available (yes / no)
main_challenge       none, no food, no water, caregiver absent, building damage, weather, other
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from irerero import audit
from irerero.config import USER
from irerero.db.models import CentreCheckin
from irerero.roles import CAREGIVER, User

CHALLENGES = {
    "none": ("None", "Nta kibazo"),
    "no_food": ("No food", "Nta biryo"),
    "no_water": ("No water", "Nta mazi"),
    "caregiver_absent": ("Caregiver absent", "Umurezi ntiyaje"),
    "building_damage": ("Building damage", "Inyubako yangiritse"),
    "weather": ("Weather", "Ikirere"),
    "other": ("Other", "Ikindi"),
}
# English / Kinyarwanda labels for the form. Kinyarwanda is a draft until reviewed.
LABELS = {
    "month": ("Month", "Ukwezi"),
    "enrolled": ("Children enrolled", "Abana banditswe"),
    "attendance_avg": ("Children present on an average day", "Abana baza ku munsi ugereranyije"),
    "caregivers_present": ("Caregivers present on an average day", "Abarezi baza ku munsi"),
    "meal_days_avg": (
        "Days a week a meal was served (0 to 6)",
        "Iminsi ifunguro ryatanzwe mu cyumweru (0-6)",
    ),
    "water_available": ("Water and handwashing available", "Amazi n'aho gukarabira birahari"),
    "main_challenge": ("Main challenge this month", "Ikibazo cy'ingenzi uku kwezi"),
}
FEW_MEAL_DAYS = 3.0
ATTENDANCE_DROP = 0.15  # 15 points below the centre's previous three months


@dataclass(frozen=True)
class Checkin:
    centre_id: str
    month: str
    enrolled: int
    attendance_avg: float
    caregivers_present: int
    meal_days_avg: float
    water_available: bool
    main_challenge: str


def validate(c: Checkin) -> list[str]:
    errors = []
    if len(c.month) != 7 or c.month[4] != "-":
        errors.append("Month must be YYYY-MM.")
    if c.enrolled < 0 or c.attendance_avg < 0 or c.caregivers_present < 0:
        errors.append("Counts cannot be negative.")
    if c.attendance_avg > c.enrolled:
        errors.append("Children present cannot be more than children enrolled.")
    if not 0 <= c.meal_days_avg <= 6:
        errors.append("Meal days must be between 0 and 6.")
    if c.main_challenge not in CHALLENGES:
        errors.append("Pick a main challenge from the list.")
    return errors


def submit(eng: Engine, user: User, c: Checkin, status: str = USER) -> int:
    """Insert or replace the centre's check-in for the month. Only the centre's caregiver."""
    if user.role != CAREGIVER or user.centre_id != c.centre_id:
        raise PermissionError("only the centre's caregiver submits its check-in")
    errors = validate(c)
    if errors:
        raise ValueError(" ".join(errors))
    with Session(eng) as s:
        row = s.scalars(
            select(CentreCheckin).where(
                CentreCheckin.centre_id == c.centre_id, CentreCheckin.month == c.month
            )
        ).first()
        before = None
        if row is None:
            row = CentreCheckin(centre_id=c.centre_id, month=c.month)
            s.add(row)
        else:
            before = {"enrolled": row.enrolled, "attendance_avg": row.attendance_avg}
        for field in (
            "enrolled",
            "attendance_avg",
            "caregivers_present",
            "meal_days_avg",
            "water_available",
            "main_challenge",
        ):
            setattr(row, field, getattr(c, field))
        row.submitted_by = user.user_id
        row.submitted_at = audit.now()
        row.status = status
        s.flush()
        audit.write(
            s,
            user,
            "checkin.submit",
            "centre_checkin",
            f"{c.centre_id}:{c.month}",
            before=before,
            after={
                "water_available": c.water_available,
                "meal_days_avg": c.meal_days_avg,
                "main_challenge": c.main_challenge,
            },
        )
        s.commit()
        return row.id


def frame(eng: Engine, centre_ids: list[str] | None = None) -> pd.DataFrame:
    query = select(CentreCheckin)
    if centre_ids is not None:
        query = query.where(CentreCheckin.centre_id.in_(centre_ids))
    with Session(eng) as s:
        rows = [
            {c.name: getattr(r, c.name) for c in CentreCheckin.__table__.columns}
            for r in s.scalars(query)
        ]
    out = pd.DataFrame(rows, columns=[c.name for c in CentreCheckin.__table__.columns])
    out["attendance_rate"] = out.attendance_avg / out.enrolled.where(out.enrolled > 0)
    return out.sort_values(["centre_id", "month"]).reset_index(drop=True)


def problems(checkins: pd.DataFrame) -> pd.DataFrame:
    """Latest check-in per centre with flags: no_water, few_meals, attendance_drop."""
    if checkins.empty:
        return checkins.assign(no_water=False, few_meals=False, attendance_drop=False)
    rows = []
    for _centre, group in checkins.groupby("centre_id"):
        group = group.sort_values("month")
        last = group.iloc[-1]
        before = group.iloc[-4:-1].attendance_rate
        drop = bool(len(before) and before.mean() - last.attendance_rate >= ATTENDANCE_DROP)
        rows.append(
            {
                **last.to_dict(),
                "no_water": not bool(last.water_available),
                "few_meals": float(last.meal_days_avg) < FEW_MEAL_DAYS,
                "attendance_drop": drop,
                "previous_rate": float(before.mean()) if len(before) else None,
            }
        )
    return pd.DataFrame(rows)


def current_month(today: date | None = None) -> str:
    today = today or date.today()
    return f"{today.year:04d}-{today.month:02d}"
