"""Simulated LEARN data for the Muhanga pilot (seed 2026): one fictional caregiver per centre in
the simulated NCDA extract, six months of check-ins and course progress. Every row is marked
simulated. Three problems are planted in Cyeza sector, so the triggers and the officer view
have something to show:

    SIM-MUH-001  no water and handwashing in the latest month   -> WASH course flagged
    SIM-MUH-002  meals on fewer than 3 days for two months      -> nutrition course flagged
    SIM-MUH-003  attendance falls from about 85% to about 50%   -> follow-up for the officer

Runs once, into empty app tables; real submissions are never overwritten.
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from irerero.config import SEED, SIMULATED
from irerero.db.models import AppUser, Assignment, CentreCheckin, SupplyExtract
from irerero.learn.progress import JOINING
from irerero.roles import CAREGIVER

MONTHS = ("2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09")
DEMO_CAREGIVER = "demo-caregiver"
NO_WATER, FEW_MEALS, DROP = "SIM-MUH-001", "SIM-MUH-002", "SIM-MUH-003"
JOINED = date(2026, 3, 1)
LESSON_COUNT = {"ecd_standards": 4, "safeguarding": 3}


def caregiver_id(centre_id: str) -> str:
    return DEMO_CAREGIVER if centre_id == NO_WATER else f"sim-cg-{centre_id[-3:]}"


def seed(eng: Engine) -> bool:
    with Session(eng) as s:
        if s.scalar(select(func.count()).select_from(CentreCheckin)):
            return False
        centres = s.scalars(select(SupplyExtract).where(SupplyExtract.status == SIMULATED)).all()
        if not centres:
            return False
        rng = np.random.default_rng(SEED)
        existing = set(s.scalars(select(AppUser.user_id)))
        for c in centres:
            cid = caregiver_id(c.centre_id)
            if cid not in existing:
                s.add(
                    AppUser(
                        user_id=cid,
                        role=CAREGIVER,
                        name=f"Simulated caregiver, {c.name}",
                        district_id="D-MUHANGA",
                        sector_id=c.geo_id,
                        centre_id=c.centre_id,
                    )
                )
            base_rate = rng.uniform(0.72, 0.9)
            meals = rng.uniform(3.5, 5.5)
            for i, month in enumerate(MONTHS):
                enrolled = int(c.enrolled_3_5 + rng.integers(-2, 3))
                rate = float(np.clip(base_rate + rng.normal(0, 0.03), 0.4, 0.98))
                meal_days = float(np.clip(meals + rng.normal(0, 0.3), 0, 6))
                water, challenge = True, "none"
                if c.centre_id == NO_WATER and month == MONTHS[-1]:
                    water, challenge = False, "no_water"
                if c.centre_id == FEW_MEALS and i >= len(MONTHS) - 2:
                    meal_days, challenge = 1.5, "no_food"
                if c.centre_id == DROP:
                    rate = (0.85, 0.84, 0.86, 0.83, 0.66, 0.52)[i]
                    if i >= 4:
                        challenge = "weather" if i == 4 else "other"
                s.add(
                    CentreCheckin(
                        centre_id=c.centre_id,
                        month=month,
                        enrolled=max(enrolled, 0),
                        attendance_avg=round(rate * max(enrolled, 0), 1),
                        caregivers_present=max(int(c.caregivers) - int(rng.random() < 0.15), 0),
                        meal_days_avg=round(meal_days, 1),
                        water_available=water,
                        main_challenge=challenge,
                        submitted_by=cid,
                        submitted_at=datetime(2026, int(month[5:]), 28, 10, 0),
                        status=SIMULATED,
                    )
                )
            for course_id in JOINING:
                done = rng.random()
                demo = cid == DEMO_CAREGIVER
                completed = (course_id == "ecd_standards") if demo else done < 0.75
                count = LESSON_COUNT[course_id]
                lessons = (
                    list(range(1, count + 1)) if completed else ([1] if demo or done < 0.85 else [])
                )
                s.add(
                    Assignment(
                        caregiver_id=cid,
                        course_id=course_id,
                        trigger="joining",
                        required_by="joining",
                        confirmed_by=None,
                        due_date=(date(2026, 11, 15) if demo else JOINED + timedelta(days=150)),
                        lessons_done=lessons,
                        completed_at=(datetime(2026, 5, 20) if completed else None),
                        score=(float(rng.choice([0.8, 1.0])) if completed else None),
                        status="completed" if completed else "required",
                    )
                )
        s.commit()
        return True


def checkins_frame(eng: Engine) -> pd.DataFrame:
    from irerero.learn.checkins import frame

    return frame(eng)
