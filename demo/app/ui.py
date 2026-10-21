"""Shared pieces of the Streamlit app: the judge per mode, the threshold strip, request and answer views."""

import json
import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from jevdemo.judge import ENV_FILE, MODEL, RECORDINGS, Judge, request_body

BUCKET_COLOURS = {"accept": "#2e7d32", "review": "#b45309", "reject": "#c4242a"}
DATA_HUE = "#1d5fbf"


def has_key() -> bool:
    load_dotenv(ENV_FILE)
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def mode() -> str:
    return "live" if st.session_state.get("live") else "recorded"


@st.cache_resource
def judge(mode: str) -> Judge:
    return Judge(mode=mode)


def sidebar():
    with st.sidebar:
        key = has_key()
        st.toggle(
            "Live API calls",
            key="live",
            disabled=not key,
            help="Off: replay recorded answers. On: call TypeSafe for every request.",
        )
        recorded = sum(1 for line in RECORDINGS.open() if line.strip())
        st.caption(
            f"Model {MODEL} · {recorded} recorded answers"
            + ("" if key else " · no TYPESAFE_API_KEY in demo/.env, live is off")
        )
        st.caption("Synthetic data only.")


# Theme config can't reach these: digits that keep their width, and a page margin on narrow screens.
CSS = """
<style>
body { font-variant-numeric: tabular-nums; }
@media (max-width: 1024px) {
  [data-testid="stMainBlockContainer"] { padding-left: 24px !important; padding-right: 24px !important; }
}
</style>
"""


def header(title: str, notebook: str):
    """Title, source line, and a slot under them for the station's finding (filled once computed)."""
    st.html(CSS)
    st.title(title)
    st.caption(f"Notebook twin: notebooks/{notebook} · answers: {mode()}")
    return st.empty()


def strip(
    df: pd.DataFrame,
    x: str,
    y: str,
    rules: list[float],
    tooltip: list[str],
    colour: str | None = "decision",
    height: int = 220,
):
    """Every judged value as a dot on 0..1, one lane per `y`, with the thresholds as rules."""
    base = alt.Chart(df).transform_calculate(jitter="random()")
    encode = {
        "x": alt.X(f"{x}:Q", scale=alt.Scale(domain=[0, 1]), title=x),
        "y": alt.Y(f"{y}:N", title=None),
        "yOffset": alt.YOffset("jitter:Q"),
        "tooltip": tooltip,
    }
    if colour:
        present = [
            b for b in BUCKET_COLOURS if b in set(df[colour])
        ]  # no legend entry without dots
        encode["color"] = alt.Color(
            f"{colour}:N",
            scale=alt.Scale(domain=present, range=[BUCKET_COLOURS[b] for b in present]),
            legend=alt.Legend(orient="top", title=None),
        )
    dots = base.mark_circle(size=70, opacity=0.8, color=DATA_HUE).encode(**encode)
    lines = (
        alt.Chart(pd.DataFrame({"t": rules}))
        .mark_rule(color="#141414", strokeDash=[4, 3])
        .encode(x="t:Q")
    )
    chart = (
        (dots + lines)
        .properties(height=height)
        .configure_axis(
            grid=False,
            labelColor="#3d3d3d",
            titleColor="#3d3d3d",
            labelFontSize=12,
            titleFontSize=12,
            labelLimit=220,
        )
        .configure_legend(labelColor="#3d3d3d", labelFontSize=12)
    )
    st.altair_chart(chart, width="stretch")


def request_view(state, questions, label="What Jev receives"):
    with st.expander(label):
        st.code(
            json.dumps(request_body(state, questions), indent=2, ensure_ascii=False),
            language=None,  # plain ink: the highlighter colours fail contrast on the code ground
            wrap_lines=True,
        )


def answer_caption(answer) -> str:
    return f"{answer.source} · {answer.latency_ms} ms"


def percent(x: float) -> str:
    return f"{x:.0%}"


P_COLUMN = st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)
