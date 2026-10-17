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
    "national": st.Page("views/national.py", title="National overview", icon=":material/public:"),
    "priorities": st.Page(
        "views/priorities.py", title="District priorities", icon=":material/format_list_numbered:"
    ),
    "sector": st.Page("views/sector.py", title="Sector profile", icon=":material/troubleshoot:"),
    "plan": st.Page("views/plan.py", title="Plan builder and tracker", icon=":material/checklist:"),
    "caregiver": st.Page("views/caregiver.py", title="Caregiver home", icon=":material/home:"),
    "officer": st.Page("views/officer.py", title="Training", icon=":material/school:"),
    "methods": st.Page("views/methods.py", title="Data and methods", icon=":material/dataset:"),
}
BY_ROLE = {
    PLANNER: ["national", "priorities", "sector", "plan", "methods"],
    ANALYST: ["national", "priorities", "sector", "plan", "methods"],
    OFFICER: ["officer", "sector", "plan", "methods"],
    CAREGIVER: ["caregiver", "methods"],
    ADMIN: ["methods"],
}

st.navigation([PAGES[key] for key in BY_ROLE[user.role]]).run()
