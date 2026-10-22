"""What the question-wording experiments taught us; the text lives in docs/lessons-learned.md."""

from pathlib import Path

import streamlit as st

DOC = Path(__file__).resolve().parent.parent / "docs" / "lessons-learned.md"

st.markdown(DOC.read_text())
