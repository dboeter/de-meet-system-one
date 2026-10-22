"""The opening page: every station's question and its result, one row each, in pipeline order."""

import html
from pathlib import Path

import results
import streamlit as st

import ui
from jevdemo import dq, er, pipeline

st.html(ui.CSS)
st.title("Code for the clear cases, Jev for the rest")
st.html(
    '<p class="support">Four stations of a data pipeline on synthetic data. Code settles what it can. '
    "Jev, TypeSafe's System One model, answers the ambiguous rows with a probability, and a threshold "
    "turns that into accept, review or reject.</p>"
)

mode = ui.mode()
judgments, _, _ = results.dq_judgments(mode)
scores = {
    "Levenshtein": er.evaluate(results.er_baseline(), results.ER_GOLD),
    "Jev": er.evaluate(
        {
            (m["id_a"], m["id_b"]): m["decision"]
            for m in results.er_matches(results.er_p_same(mode), er.LO, er.HI)
        },
        results.ER_GOLD,
    ),
}
decided = results.schema_mappings(mode)

STATIONS = [
    (
        "stations/dq.py",
        "Data quality",
        "Does this value pass the check?",
        results.dq_claim(
            dq.run(results.ROWS, results.CHECKS, judgments, pipeline.LO, pipeline.HI)
        ),
    ),
    (
        "stations/er.py",
        "Entity resolution",
        "Are these two suppliers the same organisation?",
        results.er_claim(scores),
    ),
    (
        "stations/schema.py",
        "Schema mapping",
        "Which target column holds this source column's data?",
        results.schema_claim(results.schema_table(decided)),
    ),
    (
        "stations/pii.py",
        "PII screening",
        "Does this note reveal something personal?",
        results.pii_claim(results.pii_routed(results.pii_probs(mode))),
    ),
]


def card(page, name, question, claim):
    # The "station-" key prefix is what ui.CSS styles as a clickable card.
    with st.container(border=True, key=f"station-{Path(page).stem}"):
        left, right = st.columns([2, 3], gap="large", vertical_alignment="center")
        with left:
            st.page_link(page, label=name, icon=":material/arrow_forward:")
            st.caption(question)
        right.html(f'<p class="station-claim">{html.escape(claim)}</p>')


st.subheader("Stations")
for station in STATIONS:
    card(*station)

st.subheader("Notes")
card(
    "lessons.py",
    "Lessons learned",
    "What did rewording the questions change?",
    results.LESSONS_CLAIM,
)
