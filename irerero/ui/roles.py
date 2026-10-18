"""The demo role picker. Roles and demo users live in irerero.roles."""

import os

import streamlit as st

from irerero.roles import (  # noqa: F401  (re-exported for the screens)
    ADMIN,
    ANALYST,
    CAREGIVER,
    DEMO_USERS,
    OFFICER,
    PLANNER,
    ROLE_LABELS,
    User,
)


def demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def current() -> User:
    return st.session_state.get("user", DEMO_USERS[0])


def selector(districts: dict[str, str]) -> User:
    """Sidebar role picker. In demo mode the planner's district can be changed, so every
    district can be explored; a deployed system would fix it per account."""
    with st.sidebar:
        st.markdown(
            '<div class="ir-side-label">Demo role</div><div class="ir-side-note">Fictional users, '
            "no personal data. A deployment would sign people in.</div>",
            unsafe_allow_html=True,
        )
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
