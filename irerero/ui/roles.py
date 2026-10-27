"""The demo role picker. Roles and demo users live in irerero.roles."""

import os
from html import escape

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
from irerero.ui.i18n import role, t


def demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def current() -> User:
    return st.session_state.get("user", DEMO_USERS[0])


def selector(districts: dict[str, str]) -> User:
    """Sidebar role picker. In demo mode the planner's district can be changed, so every
    district can be explored; a deployed system would fix it per account."""
    with st.sidebar:
        st.markdown(
            f'<div class="ir-side-label">{escape(t("Demo role"))}</div><div class="ir-side-note">'
            f"{escape(t('Fictional users, no personal data. A deployment would sign people in.'))}"
            "</div>",
            unsafe_allow_html=True,
        )
        old = current()
        index = next(i for i, u in enumerate(DEMO_USERS) if u.role == old.role)
        choice = st.radio(  # positions, so the chosen role survives a change of language
            t("Role"),
            range(len(DEMO_USERS)),
            index=index,
            format_func=[role(u.role, ROLE_LABELS[u.role]) for u in DEMO_USERS].__getitem__,
            label_visibility="collapsed",
        )
        user = DEMO_USERS[choice]
        if user.role == PLANNER:
            ids = list(districts)
            default = old.district_id if old.role == PLANNER else user.district_id
            district = st.selectbox(
                t("Planner's district (demo)"),
                ids,
                index=ids.index(default) if default in ids else 0,
                format_func=districts.get,
            )
            user = User(user.user_id, user.role, user.name, district_id=district)
        st.session_state["user"] = user
        return user
