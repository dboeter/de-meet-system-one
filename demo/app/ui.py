"""Shared pieces of the Streamlit app: the judge per mode, the threshold strip, request and answer views."""

import html
import json
import os
from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from jevdemo.judge import ENV_FILE, MODEL, RECORDINGS, Judge, request_body

BUCKET_COLOURS = {"accept": "#2e7d32", "review": "#b45309", "reject": "#c4242a"}
DATA_HUE = "#1d5fbf"


@dataclass
class Claim:
    """A station's result: one sentence that leads, and the line that backs it up."""

    headline: str
    support: str


def has_key() -> bool:
    load_dotenv(ENV_FILE)
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def mode() -> str:
    return "live" if st.session_state.get("live") else "recorded"


def presenting() -> bool:
    """Presenter view: the claim, one chart and the live input. Off shows every table and control."""
    return st.session_state.get("presenting", False)


def end_of_presenter_view(closing=None):
    """Everything a page draws after this call is detail, shown only with presenter view off.

    In presenter view `closing` (the live input) is drawn here; otherwise the page calls it at its end.
    """
    if presenting():
        if closing:
            closing()
        st.stop()


@st.cache_resource
def judge(mode: str) -> Judge:
    return Judge(mode=mode)


def sidebar():
    with st.sidebar:
        st.toggle(
            "Presenter view",
            value=False,
            key="presenting",
            help="On: the result, one chart and the live input. Off: every table, threshold and request.",
        )
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


# Theme config can't reach these: digits that keep their width, a page margin on narrow screens,
# and the claim type. Text sizes are set for a projector at 1280 px wide.
CSS = """
<style>
body { font-variant-numeric: tabular-nums; }
@media (max-width: 1024px) {
  [data-testid="stMainBlockContainer"] { padding-left: 24px !important; padding-right: 24px !important; }
}
.claim { margin: 0; max-width: 24em; font-size: 40px; line-height: 1.15; font-weight: 500;
  letter-spacing: -0.02em; color: #0a0a0a; text-wrap: balance; }
.support { margin: 14px 0 8px; max-width: 60ch; font-size: 18px; line-height: 1.5; color: #3d3d3d; }
.station-claim { margin: 0; max-width: 32em; font-size: 17px; line-height: 1.45; color: #3d3d3d;
  text-wrap: pretty; }
/* Overview cards: the station name leads, and the link's ::after covers the card so all of it clicks. */
[class*="st-key-station-"] { position: relative; padding: 20px 24px; transition: border-color .15s, background .15s; }
[class*="st-key-station-"]:hover { border-color: #141414; background: #f7f8fa; }
[class*="st-key-station-"] [data-testid="stElementContainer"] { position: static; }
[class*="st-key-station-"] [data-testid="stPageLink"] a { padding: 0; }
[class*="st-key-station-"] [data-testid="stPageLink"] a::after { content: ""; position: absolute; inset: 0; }
[class*="st-key-station-"] [data-testid="stPageLink"] a:hover { background: none; }
[class*="st-key-station-"] [data-testid="stPageLink"] p { font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }
[class*="st-key-station-"] [data-testid="stPageLink"] a > span:first-child { order: 2; margin-left: 8px; }
[class*="st-key-station-"] [data-testid="stIconMaterial"] { font-size: 22px; transition: transform .15s; }
[class*="st-key-station-"]:hover [data-testid="stIconMaterial"] { transform: translateX(3px); }
@media (max-width: 640px) { .claim { font-size: 30px; } }
</style>
"""
# Presenter view: the page title steps back to a station name so the claim under it leads.
STATION_NAME = """
<style>
h1 { font-size: 18px !important; font-weight: 600 !important; color: #3d3d3d !important;
  padding-bottom: 6px !important; }
</style>
"""


def header(title: str, notebook: str):
    """Title, source line, and a slot under them for the station's claim (filled once computed)."""
    st.html(CSS)
    if presenting():
        st.html(STATION_NAME)
        st.title(title)
    else:
        st.title(title)
        st.caption(f"Notebook twin: notebooks/{notebook} · answers: {mode()}")
    return st.empty()


def claim(slot, c):
    """The station's result: set large in presenter view, as one bold line over its support otherwise."""
    if presenting():
        slot.html(
            f'<p class="claim">{html.escape(c.headline)}</p>'
            f'<p class="support">{html.escape(c.support)}</p>'
        )
    else:
        slot.markdown(f"**{c.headline}** {c.support}")


def strip(
    df: pd.DataFrame,
    x: str,
    y: str,
    rules: list[float],
    tooltip: list[str],
    colour: str | None = "decision",
    height: int = 220,
    x_title: str | None = None,
    names: dict[str, str] | None = None,
):
    """Every judged value as a dot on 0..1, one lane per `y`, with the thresholds as rules.

    `names` relabels the decisions in the legend, such as accept → merge.
    """
    names = {b: (names or {}).get(b, b) for b in BUCKET_COLOURS}
    if colour:
        df = df.assign(**{colour: df[colour].map(names)})
    base = alt.Chart(df).transform_calculate(jitter="random()")
    encode = {
        "x": alt.X(f"{x}:Q", scale=alt.Scale(domain=[0, 1]), title=x_title or x),
        "y": alt.Y(f"{y}:N", title=None),
        "yOffset": alt.YOffset("jitter:Q"),
        "tooltip": tooltip,
    }
    if colour:
        present = [
            b for b in BUCKET_COLOURS if names[b] in set(df[colour])
        ]  # no legend entry without dots
        encode["color"] = alt.Color(
            f"{colour}:N",
            sort=[names[b] for b in present],
            scale=alt.Scale(
                domain=[names[b] for b in present],
                range=[BUCKET_COLOURS[b] for b in present],
            ),
            legend=alt.Legend(orient="top", title=None),
        )
    big = presenting()
    font = 15 if big else 12
    dots = base.mark_circle(
        size=110 if big else 70, opacity=0.8, color=DATA_HUE
    ).encode(**encode)
    lines = (
        alt.Chart(pd.DataFrame({"t": rules}))
        .mark_rule(color="#141414", strokeDash=[4, 3])
        .encode(x="t:Q")
    )
    chart = (
        (dots + lines)
        # Room on the right: dots at 1.0 and the "1.0" tick label overhang the plot area.
        .properties(
            height=height, padding={"left": 5, "top": 5, "bottom": 5, "right": 20}
        )
        .configure_axis(
            grid=False,
            labelColor="#3d3d3d",
            titleColor="#3d3d3d",
            labelFontSize=font,
            titleFontSize=font,
            labelLimit=220,
        )
        .configure_legend(labelColor="#3d3d3d", labelFontSize=font)
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
