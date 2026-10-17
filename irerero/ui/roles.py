"""Demo roles. Every user is invented; no real names or personal data. The selector is shown
only in demo mode and says so."""

import os
from dataclasses import dataclass

import streamlit as st

PLANNER = "district_planner"
ANALYST = "national_analyst"
OFFICER = "sector_officer"
CAREGIVER = "caregiver"
ADMIN = "admin"

ROLE_LABELS = {
    PLANNER: "District planner",
    ANALYST: "National analyst",
    OFFICER: "Sector officer",
    CAREGIVER: "Caregiver / teacher",
    ADMIN: "Admin",
}


@dataclass(frozen=True)
class User:
    user_id: str
    role: str
    name: str
    district_id: str | None = None
    sector_id: str | None = None
    centre_id: str | None = None

    @property
    def can_decide(self) -> bool:
        """Approve, edit or reject plan items and set weights for their own district."""
        return self.role == PLANNER


DEMO_USERS = (
    User("demo-planner", PLANNER, "Demo planner (fictional)", district_id="D-MUHANGA"),
    User("demo-analyst", ANALYST, "Demo national analyst (fictional)"),
    User(
        "demo-officer",
        OFFICER,
        "Demo sector officer (fictional)",
        district_id="D-MUHANGA",
        sector_id="S-MUHANGA-CYEZA",
    ),
    User(
        "demo-caregiver",
        CAREGIVER,
        "Demo caregiver (fictional)",
        district_id="D-MUHANGA",
        sector_id="S-MUHANGA-CYEZA",
        centre_id="SIM-MUH-001",
    ),
    User("demo-admin", ADMIN, "Demo admin (fictional)"),
)


def demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def current() -> User:
    return st.session_state.get("user", DEMO_USERS[0])


def selector(districts: dict[str, str]) -> User:
    """Sidebar role picker. In demo mode the planner's district can be changed, so every
    district can be explored; a deployed system would fix it per account."""
    with st.sidebar:
        st.markdown("**Demo role** · fictional users, no personal data")
        labels = [ROLE_LABELS[u.role] for u in DEMO_USERS]
        old = current()
        index = next(i for i, u in enumerate(DEMO_USERS) if u.role == old.role)
        choice = st.radio("Role", labels, index=index, label_visibility="collapsed")
        user = DEMO_USERS[labels.index(choice)]
        if user.role == PLANNER:
            ids = list(districts)
            default = old.district_id if old.role == PLANNER else user.district_id
            district = st.selectbox(
                "Planner's district (demo)",
                ids,
                index=ids.index(default) if default in ids else 0,
                format_func=districts.get,
            )
            user = User(user.user_id, user.role, user.name, district_id=district)
        st.session_state["user"] = user
        return user
