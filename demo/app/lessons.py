"""What the question-wording experiments taught us; the text lives in docs/lessons-learned.md."""

from pathlib import Path

import results
import streamlit as st

import ui
from jevdemo import lessons

DOC = Path(__file__).resolve().parent.parent / "docs" / "lessons-learned.md"

finding = ui.header("Lessons learned: question wording")
judge = ui.judge(ui.mode())

ui.claim(finding, results.LESSONS_CLAIM)

st.subheader("Schema mapping: where each column landed")
st.caption(
    "One square per source column, in the same place in every run: "
    "a square that changes colour down a column is a mapping the wording changed."
)
st.altair_chart(lessons.outcome_grid(lessons.schema_outcomes(judge)), width="content")

st.subheader("Data quality: how far apart pass and fail land")
st.caption(
    "Each dot is one row's p(pass). Rows inside the grey band go to review; "
    "a better wording pushes them out to the edges."
)
st.altair_chart(lessons.margin_strips(lessons.dq_margins(judge)), width="content")

# The doc's own title would repeat the page title.
st.markdown(DOC.read_text().split("\n", 1)[1])
