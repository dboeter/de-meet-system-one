"""What the question-wording experiments taught us; the text lives in docs/lessons-learned.md."""

from pathlib import Path

import streamlit as st

import ui
from jevdemo import lessons

DOC = Path(__file__).resolve().parent.parent / "docs" / "lessons-learned.md"

finding = ui.header("Lessons learned: question wording", "05_lessons.ipynb")
judge = ui.judge(ui.mode())

finding.markdown(
    "**Clearer wording helped; splitting the cancel Choice didn't.** Schema mapping "
    "pre-fills one more column right and none wrong, and the address check leaves fewer rows "
    "for review. The split did worse, so it was not adopted."
)

st.subheader("Schema mapping: where each column landed")
st.caption(
    "One square per source column, in the same place in every run: "
    "a square that changes colour down a column is a mapping the wording changed."
)
st.altair_chart(lessons.outcome_grid(lessons.schema_outcomes(judge)), width="content")

st.subheader("Data quality: how far apart pass and fail land")
st.caption(
    "Each dot is one row's p(pass). Rows inside the grey band go to a person; "
    "a better wording pushes them out to the edges."
)
st.altair_chart(lessons.margin_strips(lessons.dq_margins(judge)), width="content")

# The doc's own title would repeat the page title.
st.markdown(DOC.read_text().split("\n", 1)[1])
