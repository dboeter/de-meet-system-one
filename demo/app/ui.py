"""Shared pieces of the Streamlit app: the judge per mode, the threshold strip, request and answer views."""

import json
import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from jevdemo.judge import ENV_FILE, Judge, LiveUnavailable, NotRecorded, request_body

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


@st.cache_resource
def guided_step() -> dict:
    """The guided step on screen, for the notes window. Held per server: one presenter at a time."""
    return {}


def sidebar():
    with st.sidebar:
        key = has_key()
        st.toggle(
            "Live API calls",
            key="live",
            disabled=not key,
            help="Off: replay recorded answers. On: call TypeSafe for every request.",
        )
        if not key:
            st.caption("No TYPESAFE_API_KEY in demo/.env, live is off.")
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


def header(title: str):
    """Title, and a slot under it for the station's claim (filled once computed)."""
    st.html(CSS)
    st.title(title)
    return st.empty()


def claim(slot, headline: str):
    """The station's result in one sentence; the chart and numbers under it carry the rest."""
    slot.markdown(f"**{headline}**")


def strip(
    df: pd.DataFrame,
    x: str,
    y: str,
    rules: list[float],
    tooltip: list[str],
    colour: str | None = "decision",
    height: int = 260,
    x_title: str = "Probability of yes",
    title: str = "",
    subtitle: str = "",
    jitter: bool = True,
):
    """Every judged value as a dot on 0..1, one lane per `y`, with the thresholds as rules.

    `title` is the question the dots answer; it sits above the chart, where it is read first.
    `jitter=False` is for one dot per lane: the lanes are then sorted by value, highest on top,
    and the chart grows a row per lane (`height` counts title, legend and axis too).
    """
    if not jitter:
        height = 130 + 22 * df[y].nunique()
    base = alt.Chart(df).transform_calculate(jitter="random()")
    encode = {
        "x": alt.X(f"{x}:Q", scale=alt.Scale(domain=[0, 1]), title=x_title),
        "y": alt.Y(
            f"{y}:N",
            title=None,
            sort=None if jitter else "-x",
            # A line at each lane's edge, so jittered dot clouds read as separate rows;
            # without padding the lanes meet and the first edge is the chart's own frame.
            scale=alt.Scale(padding=0) if jitter else alt.Undefined,
            axis=alt.Axis(grid=jitter, bandPosition=0, gridColor="#d4d4d4"),
        ),
        "tooltip": tooltip,
    }
    if jitter:
        encode["yOffset"] = alt.YOffset(
            "jitter:Q", scale=alt.Scale(domain=[-0.15, 1.15])
        )  # dots clear the lane edges
    if colour:
        present = [
            b for b in BUCKET_COLOURS if b in set(df[colour])
        ]  # no legend entry without dots
        encode["color"] = alt.Color(
            f"{colour}:N",
            sort=present,
            scale=alt.Scale(
                domain=present,
                range=[BUCKET_COLOURS[b] for b in present],
            ),
            legend=alt.Legend(orient="top", title=None),
        )
    font = 12
    dots = base.mark_circle(size=70, opacity=0.8, color=DATA_HUE).encode(**encode)
    lines = (
        alt.Chart(pd.DataFrame({"t": rules}))
        .mark_rule(color="#141414", strokeDash=[4, 3])
        .encode(x="t:Q")
    )
    chart = (
        (dots + lines)
        # Room on the right: dots at 1.0 and the "1.0" tick label overhang the plot area.
        .properties(
            height=height,
            padding={"left": 5, "top": 5, "bottom": 5, "right": 20},
            title=alt.TitleParams(
                title,
                # One line per sentence: Vega cuts a subtitle at the chart's width instead of wrapping it.
                subtitle=[f"{line.rstrip('.')}." for line in subtitle.split(". ")]
                if subtitle
                else "",
                anchor="start",
                fontSize=17,
                fontWeight=600,
                color="#0a0a0a",
                subtitleFontSize=13,
                subtitleColor="#3d3d3d",
                offset=14,
            ),
        )
        .configure_axis(
            grid=False,
            labelColor="#3d3d3d",
            titleColor="#3d3d3d",
            labelFontSize=font,
            titleFontSize=font,
            labelLimit=420,
        )
        .configure_legend(labelColor="#3d3d3d", labelFontSize=font)
    )
    st.altair_chart(chart, width="stretch")


def json_view(body: dict, **kwargs):
    st.code(
        json.dumps(body, indent=2, ensure_ascii=False),
        language=None,  # plain ink: the highlighter colours fail contrast on the code ground
        wrap_lines=True,
        **kwargs,
    )


def request_view(state, questions, shape=""):
    """The request in one expander, Jev's answer to it in the next. `shape` names the question kind."""
    suffix = f": {shape}" if shape else ""
    with st.expander(f"What Jev receives{suffix}"):
        json_view(request_body(state, questions))
    with st.expander(f"What Jev answers{suffix}"):
        try:
            answer = judge(mode()).ask(state, questions)
        except (NotRecorded, LiveUnavailable) as e:
            st.caption(str(e))
        else:
            json_view(answer.response.model_dump(mode="json"))
            st.caption(answer_caption(answer))


def answer_caption(answer) -> str:
    return f"{answer.source} · {answer.latency_ms} ms"


def percent(x: float) -> str:
    return f"{x:.0%}"


P_COLUMN = st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)


def marked(value: str, right: bool | None) -> str:
    """An answer with a green or red mark for right or wrong; `None` (a review) stays unmarked."""
    return value if right is None else f"{'🟢' if right else '🔴'} {value}"


def er_verdict(decision: str, same: bool) -> str:
    """A merge decision marked against gold; review is no call, so it gets no mark."""
    return marked(
        decision, None if decision == "review" else (decision == "accept") == same
    )
