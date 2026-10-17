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
    "national": st.Page("pages/national.py", title="National overview", icon=":material/public:"),
    "priorities": st.Page(
        "pages/priorities.py", title="District priorities", icon=":material/format_list_numbered:"
    ),
    "methods": st.Page("pages/methods.py", title="Data and methods", icon=":material/dataset:"),
}
BY_ROLE = {
    PLANNER: ["national", "priorities", "methods"],
    ANALYST: ["national", "priorities", "methods"],
    OFFICER: ["methods"],
    CAREGIVER: ["methods"],
    ADMIN: ["methods"],
}

st.navigation([PAGES[key] for key in BY_ROLE[user.role]]).run()
