"""Screen 8. Data and methods: sources, definitions, status legend. Completed in a later step."""

import pandas as pd
import streamlit as st

from irerero.config import STATUSES
from irerero.ui import data, theme

theme.header("Data and methods", "Where every number comes from.")

STATUS_MEANING = {
    "observed": "Counted directly in a census, yearbook or administrative record.",
    "published estimate": "An estimate published by its producer (projections, survey rates).",
    "model estimate": "Computed by IrereroAI from observed and published inputs.",
    "user input": "Entered by a person in the app (targets, weights, decisions, check-ins).",
    "simulated": "Invented stand-in while the real file is missing. Never a real value.",
}
st.subheader("Status legend")
for status in STATUSES:
    st.markdown(f"{theme.badge(status)} {STATUS_MEANING[status]}", unsafe_allow_html=True)

st.subheader("Sources")
sources = data.sources().reset_index()
st.dataframe(
    pd.DataFrame(
        {
            "Source": sources.title,
            "Publisher": sources.publisher,
            "Reference period": sources.reference_period,
            "Licence": sources.licence,
            "Loaded": sources.loaded.map({True: "real file", False: "simulated stand-in"}),
        }
    ),
    hide_index=True,
    use_container_width=True,
)
