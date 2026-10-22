"""Streamlit twin of the notebooks. Run from demo/: `uv run streamlit run app/streamlit_app.py`."""

from pathlib import Path

import streamlit as st

import ui

st.set_page_config(page_title="Jev pipeline demo", layout="wide")
st.logo(str(Path(__file__).parent / "static" / "mark.svg"), size="large")

page = st.navigation(
    {
        "": [
            st.Page("guided.py", title="Guided walkthrough", url_path="guided"),
            st.Page("overview.py", title="Overview", default=True),
            st.Page(
                "notes.py", title="Speaker notes", url_path="notes", visibility="hidden"
            ),
        ],
        "Stations": [
            st.Page("stations/dq.py", title="Data quality"),
            st.Page("stations/er.py", title="Entity resolution"),
            st.Page("stations/schema.py", title="Schema mapping"),
            st.Page("stations/pii.py", title="PII screening"),
        ],
        "Notes": [st.Page("lessons.py", title="Lessons learned")],
    }
)
ui.sidebar()
page.run()
