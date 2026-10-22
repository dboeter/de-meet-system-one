"""The guided walkthrough: 13 steps, example first, for people who have never seen a System One model.

The station pages stay as they are, for questions. `STEPS` is the one registry the page, the sidebar and
the tests rely on, and the current step lives only in the URL (`?step=N`).
"""

import base64
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import dq, er, pii, pipeline, schema
from jevdemo.judge import LiveUnavailable, NotRecorded, request_body

NEUTRAL = "#3d3d3d"
ROUTE_COLOURS = {
    "excluded": ui.BUCKET_COLOURS["reject"],
    "restricted": ui.BUCKET_COLOURS["review"],
    "masked": NEUTRAL,
    "clear": NEUTRAL,
}
BASELINE_GREY = "#8b9099"
# Why a schema mapping landed where it did, keyed by schema.decide's reason.
DECISION_LINES = {
    "": "accept",
    "1:1 conflict": "review: another column took it",
    "low confidence": "review: Jev unsure",
}

ROUTE_LINES = {
    "excluded": "Health or Art. 9 data. The row stays out of gold.",
    "restricted": "Jev found another kind of personal data. It says whether, not where, so the row is restricted.",
    "masked": "Regex found a number. Code knows the span, so it masks it.",
    "clear": "Nothing found. The row goes on as it is.",
}


CSS = """
<style>
/* Streamlit's header lies over the top 56px and catches clicks there, with or without a background:
   start below it, or it covers the top of Back and Next. */
[data-testid="stMainBlockContainer"] { padding-top: 4.5rem; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: 1.75rem; }
.claim { font-size: 36px; }
.support { margin: 12px 0 0; }
.st-key-guided-eyebrow p { margin: 0; font-size: 14px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: #3d3d3d; }
.st-key-guided-pgup, .st-key-guided-pgdn { display: none; }
.g-quote { margin: 0; padding-left: 16px; border-left: 3px solid #141414; max-width: 40em;
  font-size: 20px; line-height: 1.4; text-wrap: pretty; }
.g-quote.data { font-size: 26px; }
.g-quote code { padding: 1px 6px; border-radius: 4px; background: #f0f0f0; font-size: .85em; }
.g-quote + .g-verdict { padding-left: 19px; }
.g-codes { display: grid; grid-template-columns: auto 1fr; gap: 2px 14px; margin-top: 8px;
  padding-left: 19px; font-size: 14px; color: #3d3d3d; }
.g-codes code { font-size: 13px; }
.g-label { margin: 0 0 6px; font-size: 12px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: #3d3d3d; }
.g-records + .g-label { margin-top: 14px; }
/* One grid per answer list, so the bars and chips line up from row to row. */
.g-answers { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(80px, 110px) auto;
  align-items: center; gap: 12px 14px; max-width: 560px; }
.g-answers .g-group { grid-column: 1 / -1; margin-top: 6px; font-size: 14px; color: #3d3d3d; }
.g-answers .g-group b { color: #0a0a0a; }
.g-answers .g-group-short { grid-column: 1 / 4; }
.g-answers .g-group-short + .g-chip { margin-top: 6px; }
.g-head { padding-bottom: 4px; border-bottom: 1px solid #e6e6e6; font-size: 12px; color: #5f5f5f; }
.g-head-p { grid-column: span 2; }
.g-quote.small { margin: 10px 0 2px; font-size: 16px; }
.g-gap { height: 20px; }
.g-p { text-align: right; color: #3d3d3d; }
.g-bar { position: relative; height: 10px; border-radius: 5px; background: #e6e6e6; }
.g-bar i { position: absolute; top: 0; bottom: 0; left: 0; border-radius: 5px; }
.g-bar b { position: absolute; top: -4px; bottom: -4px; width: 2px; margin-left: -1px; background: #141414; }
.g-chip { display: inline-block; padding: 2px 10px; border-radius: 999px; color: #fff; font-size: 13px;
  font-weight: 600; white-space: nowrap; }
.g-verdict { display: flex; align-items: center; gap: 10px; padding-top: 8px; font-size: 14px; color: #3d3d3d; }
.g-source { margin: 10px 0 8px; font-size: 14px; color: #3d3d3d; }
.g-source b { color: #0a0a0a; }
.g-source div { margin-top: 2px; }
.g-small { margin-top: 14px; padding-top: 2px; border-top: 1px solid #e6e6e6; }
.g-records, .g-notes { width: 100%; border-collapse: collapse; font-size: 14px; }
.g-records th, .g-records td, .g-notes th, .g-notes td { padding: 5px 10px 5px 0; text-align: left;
  vertical-align: top; border-bottom: 1px solid #e6e6e6; }
.g-records th, .g-notes th { font-weight: 500; color: #3d3d3d; }
.g-records td.g-diff { font-weight: 600; }
.g-pair { display: grid; grid-template-columns: 2fr 3fr; gap: 24px; align-items: start;
  padding: 10px 0; border-bottom: 1px solid #e6e6e6; }
.g-pair .g-names div { padding: 3px 0; }
.g-pair .g-names span { margin-right: 8px; color: #3d3d3d; font-size: 13px; }
.g-pair .g-answers { row-gap: 4px; }
.g-figs { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 24px; }
.g-fig b { display: block; font-size: 30px; font-weight: 500; line-height: 1.2; }
.g-fig span { display: block; font-size: 14px; color: #3d3d3d; }
.g-fig small { display: block; margin-top: 4px; font-size: 13px; color: #5f5f5f; }
.g-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.g-card { padding: 10px 16px; border: 1px solid #e6e6e6; border-radius: 8px; background: #f7f8fa;
  font-size: 14px; line-height: 1.5; }
.g-card b { margin-right: 6px; font-size: 17px; }
.g-cards.g-stack { grid-template-columns: 1fr; gap: 8px; max-width: 560px; }
.g-stations { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.g-station { position: relative; padding: 16px 20px 16px 64px; border: 1px solid #cfd3da;
  border-left: 4px solid #1d5fbf; border-radius: 10px; background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, .06); }
.g-station h3 { margin: 0 0 10px; padding: 0; font-size: 20px; font-weight: 600; }
.g-station .g-num { position: absolute; top: 16px; left: 18px; display: grid; place-items: center;
  width: 32px; height: 32px; border-radius: 50%; background: #1d5fbf; color: #fff; font-weight: 600; }
.g-station dl { display: grid; grid-template-columns: 40px 1fr; gap: 6px 10px; margin: 0; font-size: 14px; }
.g-station dt { font-size: 12px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  color: #5f5f5f; padding-top: 2px; }
.g-station dt.g-jev-ink { color: #1d5fbf; }
.g-station dd { margin: 0; color: #3d3d3d; }
.g-station dd.g-ask { color: #0a0a0a; font-size: 16px; line-height: 1.35; }
</style>
"""


@dataclass(frozen=True)
class Step:
    section: str  # the eyebrow
    title: str  # the outline label; also the headline on example steps
    note: str  # the speaker note
    render: Callable[[], None]  # draws the body, headline included


def current() -> int:
    """The step in the URL, 1-based: clamped to the deck, 1 when it isn't a number."""
    try:
        n = int(st.query_params.get("step", "1"))
    except ValueError:
        return 1
    return min(max(n, 1), len(STEPS))


def step() -> Step:
    return STEPS[current() - 1]


def move(by: int):
    st.query_params["step"] = str(min(max(current() + by, 1), len(STEPS)))


# --- HTML pieces ---


def chip(label: str, colour: str) -> str:
    return (
        f'<span class="g-chip" style="background:{colour}">{html.escape(label)}</span>'
    )


def landing(decision: str) -> str:
    """Where a decision lands: accept, review or reject, in its colour."""
    return chip(decision, ui.BUCKET_COLOURS[decision])


def bar(p: float, ticks, fill: str) -> str:
    marks = "".join(f'<b style="left:{t * 100:g}%"></b>' for t in ticks)
    return f'<span class="g-bar"><i style="width:{p * 100:.1f}%;background:{fill}"></i>{marks}</span>'


def row(
    item: str, p: float, ticks=(), fill: str = ui.DATA_HUE, outcome: str = ""
) -> str:
    """One answer: the item, p, a bar with the thresholds ticked on it, and where it lands."""
    return (
        f'<span>{html.escape(item)}</span><span class="g-p">{p:.2f}</span>'
        f"{bar(p, ticks, fill)}{outcome or '<span></span>'}"
    )


def answers(*parts: str) -> str:
    return f'<div class="g-answers">{"".join(parts)}</div>'


def head(item: str, p: str = "Probability of yes", outcome: str = "Decision") -> str:
    """Column names over an answer list: what each row is, what the number means, where it lands."""
    return (
        f'<span class="g-head">{html.escape(item)}</span>'
        f'<span class="g-head g-head-p">{html.escape(p)}</span>'
        f'<span class="g-head">{html.escape(outcome)}</span>'
    )


def group(heading: str, outcome: str = "") -> str:
    """A heading across the answer list; with an outcome, the chip sits in the Decision column."""
    if outcome:
        return f'<div class="g-group g-group-short">{heading}</div>{outcome}'
    return f'<div class="g-group">{heading}</div>'


def verdict(outcome: str = "", before: str = "", after: str = "") -> str:
    """A line under an answer: text, then the outcome chip, then text."""

    def text(s: str) -> str:
        return f"<span>{html.escape(s)}</span>" if s else ""

    return f'<div class="g-verdict">{text(before)}{outcome}{text(after)}</div>'


def label(text: str) -> str:
    return f'<p class="g-label">{html.escape(text)}</p>'


def quote(text: str, data: bool = False, small: bool = False) -> str:
    """The question word for word; `field` names are set as code."""
    body = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))
    kind = " data" if data else " small" if small else ""
    return f'<blockquote class="g-quote{kind}">{body}</blockquote>'


def lead(headline: str, support: str = ""):
    """The headline, and at most one sentence under it."""
    under = f'<p class="support">{html.escape(support)}</p>' if support else ""
    st.html(f'<p class="claim">{html.escape(headline)}</p>{under}')


def figures(*items: tuple[str, object, str]):
    """Numbers in a row, each with its label and an optional line under it."""
    cells = "".join(
        f'<div class="g-fig"><b>{html.escape(str(value))}</b><span>{html.escape(name)}</span>'
        f"{f'<small>{html.escape(note)}</small>' if note else ''}</div>"
        for name, value, note in items
    )
    st.html(f'<div class="g-figs">{cells}</div>')


def static_table(df: pd.DataFrame):
    # Not st.dataframe: a grid that was clicked keeps the arrow keys and PageDown, and with them the clicker.
    st.table(df, hide_index=True)


def judge():
    return ui.judge(ui.mode())


def example(top: str, state, questions):
    """The question on the left with the answers under it, the request on the right.

    The left column is returned with `top` in it, so the answers land right under their question.
    """
    left, right = st.columns([3, 2], gap="large")
    if top:
        left.html(top)
    with right:
        st.html(label("The request"))
        body = request_body(state, questions)
        body.pop("model")  # the same on every step; the room reads state and questions
        st.code(
            json.dumps(body, indent=2, ensure_ascii=False),
            language=None,  # plain ink, as in ui.request_view
            wrap_lines=True,
            height=480,
        )
    return left


# --- Examples, looked up from the data by key so their requests hash to the recorded ones ---

ER_RECORDS = {r["id"]: r for r in results.ER_A + results.ER_B}
SOURCES = {s["source_col"]: s for s in results.SOURCES}
NOTES = {n["id"]: n for n in results.NOTES}


def dq_check(check_id: str) -> dq.Check:
    return next(c for c in results.CHECKS if c.id == check_id)


def dq_value(check: dq.Check, value: str) -> str:
    if value not in {r[check.column] for r in results.ROWS}:
        raise KeyError(f"{value!r} is not a {check.column} in data/dq_rows.csv")
    return value


def dq_p(check: dq.Check, value: str, answer) -> float:
    return dq.to_judgment(check, value, answer.response).p_pass


def dq_row(check: dq.Check, value: str, answer) -> str:
    p = dq_p(check, value, answer)
    return row(
        value,
        p,
        [pipeline.LO, pipeline.HI],
        outcome=landing(pipeline.bucket(p)),
    )


def er_pair(a_id: str, b_id: str):
    return ER_RECORDS[a_id], ER_RECORDS[b_id]


def er_rows(ra: dict, rb: dict, p_same: float, heading: bool = True) -> str:
    """Name matching and Jev on one pair, then our label."""
    baseline = results.er_baseline()[(ra["id"], rb["id"])]
    same = (ra["id"], rb["id"]) in results.ER_GOLD
    return answers(
        head("Method", "Probability: same organisation") if heading else "",
        row(
            "Name matching (Levenshtein)",
            er.name_similarity(ra, rb),
            results.BASELINE_CUTS,
            BASELINE_GREY,
            landing(baseline),
        ),
        row(
            "Jev",
            p_same,
            [er.LO, er.HI],
            outcome=landing(pipeline.bucket(p_same, er.LO, er.HI)),
        ),
    ) + verdict(
        before=f"Correct answer: {'same organisation' if same else 'different organisations'}"
    )


def records_table(ra: dict, rb: dict) -> str:
    """Two records, field by field; where they differ the values are bold."""
    cells = "".join(
        f"<tr><th>{f}</th>"
        + "".join(
            f'<td class="g-diff">{html.escape(r[f])}</td>'
            if ra[f] != rb[f]
            else f"<td>{html.escape(r[f])}</td>"
            for r in (ra, rb)
        )
        + "</tr>"
        for f in ("name", "street", "postcode", "city", "kvk")
    )
    return f'<table class="g-records"><tr><th></th><th>Record {ra["id"]}</th><th>Record {rb["id"]}</th></tr>{cells}</table>'


def source_block(s: dict) -> str:
    comment = f"comment: {html.escape(s['comment'])}" if s["comment"] else "no comment"
    samples = " · ".join(html.escape(x) for x in s["samples"] if x)
    return (
        f'<div class="g-source"><b>{html.escape(s["source_col"])}</b> · {html.escape(s["type"])} · '
        f"{comment}<div>{samples}</div></div>"
    )


def mapping_line(decided_row: dict) -> str:
    return verdict(
        landing(decided_row["decision"]),
        after=decided_row["reason"],
    )


def pii_p(answer) -> dict[str, float]:
    return {c: answer.response.nouls[c].noul for c in pii.CATEGORIES}


def pii_bars(p: dict[str, float]) -> str:
    return answers(
        head("Kind of personal data", "Probability it's in the text", ""),
        *(
            row(results.CATEGORY_NAMES[c], p[c], [pii.THRESHOLD])
            for c in pii.CATEGORIES
        ),
    )


def route_chip(route: str) -> str:
    return chip(route, ROUTE_COLOURS[route])


# --- The 13 steps ---


def system_one():
    lead(
        step().title,
        "You send Jev a row and a question in plain words; it sends back a probability.",
    )
    check = dq_check("address_is_postal")
    value = dq_value(check, "Coolsingel 40, 3011 AD Rotterdam")
    state, questions = dq.check_request(check, value)
    answer = judge().ask(state, questions)
    # Everything reads down the left column, next to the request: answer, question kinds, then cost.
    with example(quote(questions["passes"].instructions), state, questions):
        st.html(answers(head("Value"), dq_row(check, value, answer)))
        st.html(
            label("Two kinds of question") + '<div class="g-cards g-stack">'
            '<div class="g-card"><b>Noul</b>A yes/no question. One probability that the answer is yes.</div>'
            f'<div class="g-card"><b>Choice</b>Pick one of up to {schema.MAX_OPTIONS} options. '
            "A probability for every option.</div></div>"
        )
        st.html(label("Speed and cost"))
        figures(
            ("per question (median)", "~215 ms", ""),
            ("at 16 threads", "65 rows/s", ""),
            ("per million questions", "~$13", ""),
        )


def code_and_jev():
    lead(
        step().title,
        "Code settles what rules can; Jev judges the rest.",
    )
    # st.html's sanitizer drops inline <svg>; as an image it survives, but can't use the page's web font.
    svg = base64.b64encode(pipeline_svg().encode()).decode()
    st.html(
        f'<img src="data:image/svg+xml;base64,{svg}" style="width:100%;max-width:1040px" '
        'alt="Rows go through code. A rule settles the clear yes and no; the rest go to Jev, and your '
        'thresholds sort its answer into accept, review or reject.">'
    )
    cards = "".join(
        f'<div class="g-station"><span class="g-num">{i}</span><h3>{html.escape(name)}</h3>'
        f"<dl><dt>Code</dt><dd>{html.escape(code)}</dd>"
        f'<dt class="g-jev-ink">Jev</dt><dd class="g-ask">{html.escape(ask)}</dd></dl></div>'
        for i, (name, (code, ask)) in enumerate(results.STATIONS.iterrows(), 1)
    )
    st.html(
        label("The four stations in this demo")
        + f'<div class="g-stations">{cards}</div>'
    )


def pipeline_svg(p: float = 0.73) -> str:
    """Rows through code into three lanes; the middle lane goes through Jev and the thresholds.

    The threshold bar is drawn to scale from pipeline.LO and HI, with an example answer `p` on it.
    """
    blue, grey, ink = ui.DATA_HUE, "#cfd3da", "#3d3d3d"
    colours = ui.BUCKET_COLOURS
    bar_x, bar_w = 714, 144  # the threshold bar inside its node

    def x_at(v: float) -> float:
        return bar_x + v * bar_w

    def arrow(d: str, colour: str = grey) -> str:
        return f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2" marker-end="url(#g-head)"/>'

    def box(x, y, w, h, title, sub="", stroke=grey, width=1):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#f7f8fa" stroke="{stroke}" '
            f'stroke-width="{width}"/>'
            f'<text x="{x + 16}" y="{y + 30}" class="t">{title}</text>'
            f'<text x="{x + 16}" y="{y + 52}" class="s">{sub}</text>'
        )

    def bucket_chip(name: str, cy: int) -> str:
        return (
            f'<rect x="930" y="{cy - 15}" width="90" height="30" rx="15" fill="{colours[name]}"/>'
            f'<text x="975" y="{cy + 5}" class="c">{name}</text>'
        )

    segments = (
        (0, pipeline.LO, "reject"),
        (pipeline.LO, pipeline.HI, "review"),
        (pipeline.HI, 1, "accept"),
    )
    bar = "".join(
        f'<rect x="{x_at(a)}" y="142" width="{(b - a) * bar_w}" height="10" fill="{colours[n]}"/>'
        for a, b, n in segments
    )
    rows = "".join(
        f'<rect x="20" y="{y}" width="70" height="8" rx="2" fill="{grey}"/>'
        for y in range(108, 160, 14)
    )
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 280"
 font-family="Geist, system-ui, -apple-system, 'Segoe UI', sans-serif">
<style>
 .t {{ font-size: 17px; font-weight: 600; fill: #0a0a0a; }}
 .s {{ font-size: 13px; fill: {ink}; }}
 .l {{ font-size: 13px; fill: {ink}; }}
 .c {{ font-size: 14px; font-weight: 600; fill: #fff; text-anchor: middle; }}
</style>
<defs><marker id="g-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{ink}"/></marker></defs>
<rect x="6" y="90" width="98" height="100" rx="10" fill="#f7f8fa" stroke="{grey}"/>
{rows}<text x="55" y="182" class="s" text-anchor="middle">rows</text>
{arrow("M106 140 H146")}
{box(150, 95, 236, 90, "Code", "normalize · block · exact rules")}
<text x="166" y="169" class="s">regex · cache</text>
{arrow("M388 140 C 426 140, 426 40, 464 40 H 924", colours["accept"])}
<text x="480" y="30" class="l">a rule settles it: yes</text>
{arrow("M388 140 C 426 140, 426 240, 464 240 H 924", colours["reject"])}
<text x="480" y="264" class="l">a rule settles it: no</text>
{arrow("M388 140 H 494", blue)}
<text x="436" y="130" class="l">the rest</text>
{box(498, 100, 150, 80, "Jev", f"p = {p:.2f}", blue, 2)}
{arrow("M650 140 H 694", blue)}
{box(698, 95, 176, 90, "Thresholds", "")}
{bar}<line x1="{x_at(p)}" y1="135" x2="{x_at(p)}" y2="159" stroke="#0a0a0a" stroke-width="2.5"/>
<text x="{x_at(pipeline.LO)}" y="176" class="s" text-anchor="middle">{pipeline.LO:g}</text>
<text x="{x_at(pipeline.HI)}" y="176" class="s" text-anchor="middle">{pipeline.HI:g}</text>
{arrow("M876 140 C 900 140, 900 46, 924 46", colours["accept"])}
{arrow("M876 140 H 924", colours["review"])}
{arrow("M876 140 C 900 140, 900 234, 924 234", colours["reject"])}
{bucket_chip("accept", 40)}{bucket_chip("review", 140)}{bucket_chip("reject", 240)}
</svg>"""


def dq_values():
    lead(
        step().title,
        "Type, null and range checks let all of these through.",
    )
    examples = {
        "address_is_postal": [
            "Damrak 1, 1012 LG Amsterdam",
            "Postbus 1200, 3000 BE Rotterdam",
            "bovenwoning naast de bakker",
            "zelfde als factuuradres",
        ],
        "description_names_product": [
            "zie mail",
            "zoals besproken met Petra",
            "Thinkpad zoals vorige keer",
        ],
    }
    shown = ("description_names_product", "zie mail")  # the request on the right
    checks = {cid: dq_check(cid) for cid in examples}
    asked = [
        (checks[cid], dq_value(checks[cid], v))
        for cid, values in examples.items()
        for v in values
    ]
    replies = {
        (c.id, v): a
        for (c, v), a in zip(
            asked,
            judge().ask_many([dq.check_request(c, v) for c, v in asked]),
            strict=True,
        )
    }
    parts = []
    for cid, check in checks.items():
        # Each check's own question sits right over its answers.
        _, asks = dq.check_request(check, examples[cid][0])
        parts += [group(quote(asks["passes"].instructions, small=True)), head("Value")]
        parts += [dq_row(check, v, replies[(cid, v)]) for v in examples[cid]]
    state, questions = dq.check_request(checks[shown[0]], shown[1])
    with example("", state, questions):
        st.html(answers(*parts))


def dq_choice():
    lead(
        step().title,
        "Map free text to a code list; when no code fits, 'other' is an answer too.",
    )
    check = dq_check("cancel_reason_code")
    values = [
        dq_value(check, v)
        for v in (
            "nieuwe inkoper, eigen leveranciers",
            "concurrent was goedkoper",
            "kwaliteit viel tegen",
        )
    ]
    replies = judge().ask_many([dq.check_request(check, v) for v in values])
    parts = [head("Code, top two", "Probability")]
    for value, reply in zip(values, replies, strict=True):
        probabilities = reply.response.choices["code"].probabilities
        p = dq_p(check, value, reply)
        parts.append(group(f"<b>{html.escape(value)}</b>", landing(pipeline.bucket(p))))
        parts += [
            row(code, share)
            for code, share in sorted(probabilities.items(), key=lambda kv: -kv[1])[:2]
        ]
    state, questions = dq.check_request(check, values[-1])
    codes = "".join(
        f"<code>{html.escape(c)}</code><span>{html.escape(d)}</span>"
        for c, d in check.codes.items()
    )
    with example(
        quote(questions["code"].instructions) + f'<div class="g-codes">{codes}</div>',
        state,
        questions,
    ):
        st.html(answers(*parts))


def dq_scale():
    judgments, first, rerun = results.dq_judgments(ui.mode())
    result = dq.run(results.ROWS, results.CHECKS, judgments, pipeline.LO, pipeline.HI)
    lead(results.dq_claim(result))
    figures(
        ("Row checks", len(results.ROWS) * len(results.CHECKS), ""),
        ("Questions to Jev", first.asked, ""),
        ("Questions on tomorrow's rerun", rerun.asked, ""),
    )
    distinct = (
        pd.DataFrame(result.rows)
        .drop_duplicates(["check_id", "value"])
        .assign(check=lambda t: t["check_id"].map(results.check_label))
    )
    ui.strip(
        distinct,
        "p_pass",
        "check",
        [pipeline.LO, pipeline.HI],
        ["value", "p_pass", "code", "decision"],
        height=240,
        title="Does the value pass its check?",
        subtitle=(
            f"One dot per distinct value. Left of {pipeline.LO:.2f} reject, right of {pipeline.HI:.2f} accept; "
            "in between, review."
        ),
    )


def er_same_name():
    lead(
        step().title,
        "Name matching sees identical names; Jev reads the whole record.",
    )
    ra, rb = er_pair("A02", "B02")
    state, questions = er.pair_request(ra, rb)
    answer = judge().ask(state, questions)
    with example(quote(questions["same"].instructions), state, questions):
        st.html(
            records_table(ra, rb)
            + '<div class="g-gap"></div>'
            + er_rows(ra, rb, answer.response.nouls["same"].noul)
        )


def er_other_name():
    lead(
        step().title,
        "The question's criteria say what counts as the same organisation.",
    )
    criteria = er.SAME_ORGANISATION.criteria
    st.html(
        quote(er.SAME_ORGANISATION.instructions)
        + f'<div class="g-codes"><b>yes</b><span>{html.escape(criteria["true"])}</span>'
        f"<b>no</b><span>{html.escape(criteria['false'])}</span></div>"
    )
    pairs = [er_pair("A01", "B01"), er_pair("A06", "B06"), er_pair("A09", "B08")]
    replies = judge().ask_many([er.pair_request(ra, rb) for ra, rb in pairs])
    blocks = []
    for i, ((ra, rb), reply) in enumerate(zip(pairs, replies, strict=True)):
        names = "".join(
            f"<div><span>{r['id']}</span>{html.escape(r['name'])}</div>"
            for r in (ra, rb)
        )
        rows = er_rows(ra, rb, reply.response.nouls["same"].noul, heading=i == 0)
        blocks.append(
            f'<div class="g-pair"><div class="g-names">{names}</div><div>{rows}</div></div>'
        )
    st.html("".join(blocks))


def er_scale():
    p_same = results.er_p_same(ui.mode())
    matches = results.er_matches(p_same, er.LO, er.HI)
    jev = {(m["id_a"], m["id_b"]): m["decision"] for m in matches}
    scores = {
        "Levenshtein": er.evaluate(results.er_baseline(), results.ER_GOLD),
        "Jev": er.evaluate(jev, results.ER_GOLD),
    }
    lead(results.er_claim(scores))
    figures(
        ("Possible pairs", len(results.ER_A) * len(results.ER_B), ""),
        ("After blocking", len(results.PAIRS), ""),
        ("Exact KvK/IBAN rule", len(results.EXACT), ""),
        ("Judged by Jev", len(results.AMBIGUOUS), ""),
        ("Review", scores["Jev"]["review"], ""),
    )
    names = {i: r["name"] for i, r in ER_RECORDS.items()}
    table = pd.DataFrame(matches)
    table["gold"] = [
        (x, y) in results.ER_GOLD for x, y in zip(table["id_a"], table["id_b"])
    ]
    jev_rows = table[table["by"] == "Jev"].assign(
        pair=lambda t: t["id_a"].map(names) + " | " + t["id_b"].map(names),
    )
    ui.strip(
        jev_rows,
        "p_same",
        "pair",
        [er.LO, er.HI],
        ["pair", "p_same", "decision", "gold"],
        jitter=False,
        title="Are both records the same supplier?",
        subtitle=(
            f"One dot per pair that no exact KvK or IBAN rule settled. Left of {er.LO:.2f} reject, "
            f"right of {er.HI:.2f} accept; in between, review."
        ),
    )


def schema_example():
    lead(
        step().title,
        "A legacy column without a comment: Jev picks a target from a shortlist.",
    )
    decided = {d["source_col"]: d for d in results.schema_mappings(ui.mode())}
    source, second = SOURCES["KLANT.KLT_NM_VOL"], SOURCES["KLANT.KLT_OPM"]
    state, questions = schema.mapping_request(source, results.TARGETS)
    answer = judge().ask(state, questions)
    top = sorted(
        answer.response.choices["target"].probabilities.items(), key=lambda kv: -kv[1]
    )[:4]
    pick = decided[second["source_col"]]
    with example(quote(questions["target"].instructions), state, questions):
        st.html(
            source_block(source)
            + answers(
                head("Target column, top four", "Probability", ""),
                *(row(option, p, [schema.CONFIDENT]) for option, p in top),
            )
            + mapping_line(decided[source["source_col"]])
            + '<div class="g-small">'
            + source_block(second)
            + answers(row(pick["target_col"], pick["p"], [schema.CONFIDENT]))
            + mapping_line(pick)
            + "</div>"
        )


def schema_scale():
    decided = results.schema_mappings(ui.mode())
    table = results.schema_table(decided)
    lead(results.schema_claim(table))
    accepted = table["decision"] == "accept"
    figures(
        ("Accepted", int(accepted.sum()), ""),
        ("Accepted and wrong", int((accepted & ~table["correct"]).sum()), ""),
        ("Review", int((~accepted).sum()), ""),
    )
    st.html(label("Where Jev was wrong"))
    wrong = table[~table["correct"]]
    static_table(
        wrong.assign(
            p=wrong["p"].map("{:.2f}".format),
            reason=wrong["reason"].map(DECISION_LINES),
        )[["source_col", "target_col", "p", "reason", "gold"]].rename(
            columns={
                "source_col": "Source column",
                "target_col": "Jev's pick",
                "p": "Confidence",
                "reason": "Decision",
                "gold": "Right answer",
            }
        )
    )
    with st.expander("The output: a dbt sources.yml"):
        st.code(
            schema.sources_yml(decided, source_name="legacy_crm"),
            language=None,
            wrap_lines=True,
            height=220,
        )


def pii_example():
    lead(
        step().title,
        "Regex finds numbers like BSN and IBAN, but can't read context.",
    )
    text = NOTES["N01"]["text"]
    hits = pii.regex_hits(text)
    state, questions = pii.screen_request(text)
    answer = judge().ask(state, questions)
    p = pii_p(answer)
    top = quote(text, data=True) + verdict(
        before=f"Regex found: {', '.join(sorted(hits)) or 'nothing'}"
    )
    with example(top, state, questions):
        st.html(pii_bars(p) + verdict(route_chip(pii.route(hits, p)), before="Route"))
    rows = ""
    for nid in ("N16", "N19"):
        other = NOTES[nid]["text"]
        probs = pii_p(judge().ask(*pii.screen_request(other)))
        over = [
            f"{results.CATEGORY_NAMES[c]} {probs[c]:.2f}"
            for c in pii.CATEGORIES
            if probs[c] >= pii.THRESHOLD
        ]
        rows += (
            f"<tr><td>{html.escape(other)}</td><td>{html.escape(', '.join(over)) or 'none'}</td>"
            f"<td>{route_chip(pii.route(pii.regex_hits(other), probs))}</td></tr>"
        )
    st.html(
        f'<table class="g-notes"><tr><th>More notes</th><th>At or above {pii.THRESHOLD:.2f}</th>'
        f"<th>Route</th></tr>{rows}</table>"
    )


def pii_scale():
    routed = results.pii_routed(results.pii_probs(ui.mode()))
    lead(results.pii_claim(routed))
    counts = routed["route"].value_counts()
    figures(
        *(
            (route.capitalize(), int(counts.get(route, 0)), line)
            for route, line in ROUTE_LINES.items()
        )
    )


def your_turn():
    lead(
        step().title,
        "Regex runs first; if it finds nothing, Jev screens the sentence.",
    )
    with st.form("guided-live"):
        text = st.text_area("A Dutch sentence", pii.LIVE_PRESET, height=80)
        asked = st.form_submit_button("Ask Jev", type="primary", key="guided-ask")
    if asked:
        hits = pii.regex_hits(text)
        if hits:
            st.html(
                verdict(
                    route_chip(pii.route(hits, {})),
                    before="Route",
                    after="Jev not asked",
                )
            )
            st.caption(f"regex: {', '.join(sorted(hits))}")
        else:
            try:
                answer = judge().ask(*pii.screen_request(text))
            except (NotRecorded, LiveUnavailable) as e:
                st.warning(str(e))
            else:
                p = pii_p(answer)
                st.html(
                    pii_bars(p)
                    + verdict(route_chip(pii.route(hits, p)), before="Route")
                )
                st.caption(ui.answer_caption(answer))  # live or recorded: the room asks


STEPS = [
    Step(
        "System One",
        "A System One model answers a question about your data with a probability",
        "Jev is not a chatbot. One request is data plus a question in plain words, and back comes a "
        "probability. A street name with its own house number is one building, so the address passes. "
        "Two shapes of question: "
        "a Noul for yes or no, a Choice to pick one option.",
        system_one,
    ),
    Step(
        "System One",
        "Code for the clear cases, Jev for the rest",
        "Every station has this shape, so you learn it once. Code does what code is good at: normalizing, "
        "blocking, exact rules, regex. Jev only sees the rows code can't settle. The thresholds are yours, "
        "and moving them costs no API calls.",
        code_and_jev,
    ),
    Step(
        "Data quality",
        "Values your DQ tool lets through",
        "None of these values is null or the wrong type. The check is one sentence of config, and Jev "
        "answers once per distinct value. 'Thinkpad zoals vorige keer' names a product but points "
        "elsewhere, so Jev is unsure and it goes to review.",
        dq_values,
    ),
    Step(
        "Data quality",
        "Free text to a code: a Choice",
        "'nieuwe inkoper, eigen leveranciers' never says 'switched supplier', and Jev is sure. "
        "'concurrent was goedkoper' fits two codes, price and switching supplier: a coin flip goes to "
        "review instead of a guess. For 'kwaliteit viel tegen' no code fits, so 'other' wins: review too.",
        dq_choice,
    ),
    Step(
        "Data quality",
        "Data quality at scale",
        "This is where it plugs into a medallion pipeline: a run manifest per check, a limit on the fail "
        "rate and an action. Product descriptions cross their limit, so fail_run fires. Answers are cached "
        "per check and value, so tomorrow's run asks nothing new.",
        dq_scale,
    ),
    Step(
        "Entity resolution",
        "Same name, different company",
        "Name matching says these are identical. They are two companies: a different city and a "
        "different KvK number. Jev reads the whole record and keeps them apart.",
        er_same_name,
    ),
    Step(
        "Entity resolution",
        "Different name, same organisation",
        "The other direction: a department, an abbreviation, a translated name. The criteria define what "
        "counts as the same organisation. Where Jev isn't sure, as with a hotel and a café on the same "
        "square, it goes to review.",
        er_other_name,
    ),
    Step(
        "Entity resolution",
        "Entity resolution at scale",
        "Blocking keeps the candidates small, exact KvK and IBAN rules settle the obvious ones, and Jev "
        "judges the rest. Same pairs, same rules: compare it with name matching.",
        er_scale,
    ),
    Step(
        "Schema mapping",
        "KLT_NM_VOL → ?",
        "A legacy column with no comment and a Dutch abbreviation. Jev picks from the shortlist and reads "
        "the sample values. 'none' is one of the options, so 'no target' is a valid answer, as for the "
        "free-text remarks column.",
        schema_example,
    ),
    Step(
        "Schema mapping",
        "Schema mapping at scale",
        "Pre-filled only when Jev is confident and no other column claims the same target. Every wrong "
        "pick went to review, not into the mapping. The output is a dbt sources.yml. It is below "
        "the 70% goal; most misses are abbreviations without comments.",
        schema_scale,
    ),
    Step(
        "PII screening",
        "What regex can't see",
        "Regex can't see that a neighbour with diabetes is health data about a private person. Five "
        "yes/no questions in one request. Trade-union membership is special-category data; a public "
        "official is not a private person. The union note also scores 0.36 on naming a person without "
        "naming anyone: a false flag, the price of a low threshold.",
        pii_example,
    ),
    Step(
        "PII screening",
        "PII screening at scale",
        "Regex alone finds none of these notes. The threshold is low on purpose: a missed flag costs more "
        "than a review. And the gate: this is synthetic data. Client text only after the data-residency "
        "question is settled.",
        pii_scale,
    ),
    Step(
        "Your turn",
        "Your turn",
        "Ask the room for a Dutch sentence with something personal in it. Switch on Live API calls in the "
        "sidebar first. If the network fails, the preset still answers from its recording.",
        your_turn,
    ),
]

n = current()
st.html(ui.CSS + CSS)
eyebrow, back, forward = st.columns([6, 1, 1], vertical_alignment="center")
with eyebrow:
    with st.container(key="guided-eyebrow"):
        st.markdown(f"{step().section} · {n} / {len(STEPS)}")
    # Presentation clickers send PageUp / PageDown; these two are hidden by CSS.
    st.button(
        "Previous",
        key="guided-pgup",
        shortcut="PageUp",
        disabled=n == 1,
        on_click=move,
        args=(-1,),
    )
    st.button(
        "Following",
        key="guided-pgdn",
        shortcut="PageDown",
        disabled=n == len(STEPS),
        on_click=move,
        args=(1,),
    )
back.button(
    "Back",
    key="guided-back",
    shortcut="Left",
    disabled=n == 1,
    on_click=move,
    args=(-1,),
    width="stretch",
)
forward.button(
    "Next",
    key="guided-next",
    type="primary",
    shortcut="Right",
    disabled=n == len(STEPS),
    on_click=move,
    args=(1,),
    width="stretch",
)
step().render()

ui.guided_step().update(
    n=n,
    of=len(STEPS),
    section=step().section,
    title=step().title,
    note=step().note,
    next=STEPS[n].title if n < len(STEPS) else None,
)

with st.sidebar:
    st.subheader("Speaker note")
    st.write(step().note)
    if n < len(STEPS):
        st.caption(f"Next: {STEPS[n].title}")
    st.markdown(
        "[Speaker notes in a new window](notes)"
    )  # markdown links open in a new tab
    # A new step should open at its top. The snippet sits here, at a position that doesn't depend on
    # the step's body, and carries the step number: the element only changes when the step does, so a
    # rerun on the same step ("Ask Jev", a sidebar toggle) leaves the scroll alone.
    st.html(
        f"<script>/* step {n} */ document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, 0);</script>",
        unsafe_allow_javascript=True,
    )
