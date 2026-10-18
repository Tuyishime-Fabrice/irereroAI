"""Seed the app tables that start with content: demo users, and the simulated Muhanga LEARN data
(caregivers, check-ins, course progress) with its training triggers. Idempotent, never
overwrites a row that already exists, so decisions and progress survive restarts."""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from irerero.db.models import AppUser


def seed(eng: Engine) -> None:
    from irerero.roles import DEMO_USERS

    with Session(eng) as s:
        existing = set(s.scalars(select(AppUser.user_id)))
        for u in DEMO_USERS:
            if u.user_id not in existing:
                s.add(
                    AppUser(
                        user_id=u.user_id,
                        role=u.role,
                        name=u.name,
                        district_id=u.district_id,
                        sector_id=u.sector_id,
                        centre_id=u.centre_id,
                    )
                )
        s.commit()
    from irerero.learn import simulate

    simulate.seed(eng)
