"""Streamlit twin of the four notebooks. Run from demo/: `uv run streamlit run app/streamlit_app.py`."""

from pathlib import Path

import streamlit as st

import ui

st.set_page_config(page_title="Jev pipeline demo", layout="wide")
st.logo(str(Path(__file__).parent / "static" / "mark.svg"), size="large")

page = st.navigation(
    {
        "Stations": [
            st.Page("stations/dq.py", title="Data quality"),
            st.Page("stations/er.py", title="Entity resolution"),
            st.Page("stations/schema.py", title="Schema mapping"),
            st.Page("stations/pii.py", title="PII screening"),
        ]
    }
)
ui.sidebar()
page.run()
