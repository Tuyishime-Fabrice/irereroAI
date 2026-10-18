"""IrereroAI: run with `make app` (streamlit run app/streamlit_app.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from irerero.ui import data, theme
from irerero.ui.roles import ADMIN, ANALYST, CAREGIVER, OFFICER, PLANNER, demo_mode, selector

st.set_page_config(page_title="IrereroAI", page_icon=str(theme.ICON), layout="wide")
theme.setup()
data.ensure_built()

if not demo_mode():
    st.error("Sign-in is not configured for this deployment. Set DEMO_MODE=true for the demo.")
    st.stop()

user = selector(data.districts())

PAGES = {
    "national": st.Page("views/national.py", title="Overview", icon=":material/home:"),
    "priorities": st.Page(
        "views/priorities.py", title="District priorities", icon=":material/bar_chart:"
    ),
    "sector": st.Page("views/sector.py", title="Sector diagnosis", icon=":material/troubleshoot:"),
    "plan": st.Page(
        "views/plan.py", title="Action plans & progress", icon=":material/trending_up:"
    ),
    "caregiver": st.Page(
        "views/caregiver.py", title="Caregiver learning", icon=":material/school:"
    ),
    "officer": st.Page("views/officer.py", title="Caregiver learning", icon=":material/school:"),
    "brief": st.Page("views/brief.py", title="District brief", icon=":material/description:"),
    "admin": st.Page("views/admin.py", title="Admin", icon=":material/admin_panel_settings:"),
    "methods": st.Page("views/methods.py", title="Data & methods", icon=":material/database:"),
}
BY_ROLE = {
    PLANNER: {
        "Plan and diagnose": ["national", "priorities", "sector"],
        "Track": ["plan", "brief"],
        "Reference": ["methods"],
    },
    ANALYST: {
        "Plan and diagnose": ["national", "priorities", "sector"],
        "Track": ["plan", "brief"],
        "Reference": ["methods"],
    },
    OFFICER: {
        "Learn": ["officer"],
        "Diagnose and track": ["sector", "plan"],
        "Reference": ["methods"],
    },
    CAREGIVER: {"Learn": ["caregiver"], "Reference": ["methods"]},
    ADMIN: {"Manage": ["admin"], "Reference": ["methods"]},
}

sections = {name: [PAGES[key] for key in keys] for name, keys in BY_ROLE[user.role].items()}
st.navigation(sections).run()
