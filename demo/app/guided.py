"""The guided walkthrough: 13 steps, example first, for people who have never seen a System One model.

The station pages stay as they are, for questions. `STEPS` is the one registry the page, the sidebar and
the tests rely on, and the current step lives only in the URL (`?step=N`).
"""

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

ROUTE_LINES = {
    "excluded": "Health or Art. 9 data. The row stays out of gold.",
    "restricted": "Jev found another kind of personal data. It says whether, not where, so the row is restricted.",
    "masked": "Regex found a number. Code knows the span, so it masks it.",
    "clear": "Nothing found. The row goes on as it is.",
}


CSS = """
<style>
/* A step is about one screen: less air above, between elements and in the headline. */
[data-testid="stMainBlockContainer"] { padding-top: 1.5rem; }
/* A collapsed sidebar puts the logo in the header on a white ground, over the top 56px: start below it. */
.stApp:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stMainBlockContainer"] {
  padding-top: 3.5rem; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: .75rem; }
.claim { font-size: 36px; }
.support { margin: 8px 0 4px; }
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
.g-codes.two { grid-template-columns: auto 1fr auto 1fr; }
.g-codes code { font-size: 13px; }
.g-label { margin: 0 0 6px; font-size: 12px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: #3d3d3d; }
.g-records + .g-label { margin-top: 14px; }
/* One grid per answer list, so the bars and chips line up from row to row. */
.g-answers { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(80px, 110px) auto;
  align-items: center; gap: 8px 12px; max-width: 560px; }
.g-answers .g-group { grid-column: 1 / -1; margin-top: 6px; font-size: 14px; color: #3d3d3d; }
.g-answers .g-group b { color: #0a0a0a; }
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
.g-flow { display: flex; align-items: stretch; gap: 8px; }
.g-flow .g-node { display: flex; flex-direction: column; justify-content: center; padding: 12px 14px;
  border: 1px solid #cfd3da; border-radius: 8px; background: #f7f8fa; font-size: 13px; color: #3d3d3d; }
.g-flow .g-node b { font-size: 16px; color: #0a0a0a; }
.g-flow .g-jev { border: 2px solid #1d5fbf; background: #fff; }
.g-flow .g-arrow { align-self: center; color: #3d3d3d; font-size: 20px; }
.g-flow .g-lanes { display: flex; flex: 1; flex-direction: column; justify-content: space-between; gap: 14px; }
.g-flow .g-lane { display: flex; flex: 1; align-items: center; gap: 8px; }
.g-flow .g-lane small { flex: none; font-size: 13px; color: #3d3d3d; }
.g-flow .g-rail { flex: 1; height: 0; border-top: 2px solid #cfd3da; }
.g-flow .g-buckets { display: flex; flex-direction: column; justify-content: center; gap: 8px; }
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


def landing(decision: str, names: dict[str, str]) -> str:
    """Where a decision lands: the station's own word, in the bucket colour."""
    return chip(names[decision], ui.BUCKET_COLOURS[decision])


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


def group(heading: str) -> str:
    return f'<div class="g-group">{heading}</div>'


def verdict(outcome: str = "", before: str = "", after: str = "") -> str:
    """A line under an answer: text, then the outcome chip, then text."""

    def text(s: str) -> str:
        return f"<span>{html.escape(s)}</span>" if s else ""

    return f'<div class="g-verdict">{text(before)}{outcome}{text(after)}</div>'


def label(text: str) -> str:
    return f'<p class="g-label">{html.escape(text)}</p>'


def quote(text: str, data: bool = False) -> str:
    """The question word for word; `field` names are set as code."""
    body = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))
    return f'<blockquote class="g-quote{" data" if data else ""}">{body}</blockquote>'


def lead(headline: str, support: str):
    st.html(
        f'<p class="claim">{html.escape(headline)}</p><p class="support">{html.escape(support)}</p>'
    )


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
    """Row A across the page, then Row B: the request on the right. The left column is returned for the answers."""
    st.html(top)
    left, right = st.columns([3, 2], gap="medium")
    with right:
        st.html(label("The request"))
        st.code(
            json.dumps(request_body(state, questions), indent=2, ensure_ascii=False),
            language=None,  # plain ink, as in ui.request_view
            wrap_lines=True,
            height=260,
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
        outcome=landing(pipeline.bucket(p), results.DQ_NAMES),
    )


def er_pair(a_id: str, b_id: str):
    return ER_RECORDS[a_id], ER_RECORDS[b_id]


def er_rows(ra: dict, rb: dict, p_same: float) -> str:
    """Name matching and Jev on one pair, then our label."""
    baseline = results.er_baseline()[(ra["id"], rb["id"])]
    same = (ra["id"], rb["id"]) in results.ER_GOLD
    return answers(
        row(
            "Name matching (Levenshtein)",
            er.name_similarity(ra, rb),
            results.BASELINE_CUTS,
            BASELINE_GREY,
            landing(baseline, results.ER_NAMES),
        ),
        row(
            "Jev",
            p_same,
            [er.LO, er.HI],
            outcome=landing(pipeline.bucket(p_same, er.LO, er.HI), results.ER_NAMES),
        ),
    ) + verdict(
        before=f"Our label: {'same organisation' if same else 'different organisations'}"
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
        landing(decided_row["decision"], results.SCHEMA_NAMES),
        after=decided_row["reason"],
    )


def pii_p(answer) -> dict[str, float]:
    return {c: answer.response.nouls[c].noul for c in pii.CATEGORIES}


def pii_bars(p: dict[str, float]) -> str:
    return answers(
        *(row(results.CATEGORY_NAMES[c], p[c], [pii.THRESHOLD]) for c in pii.CATEGORIES)
    )


def route_chip(route: str) -> str:
    return chip(route, ROUTE_COLOURS[route])


# --- The 13 steps ---


def system_one():
    lead(
        step().title,
        "Jev is TypeSafe's System One model. You send it a row and a question in plain words. "
        "It sends back a probability, so your code decides what happens next.",
    )
    check = dq_check("address_is_postal")
    value = dq_value(check, "Postbus 1200, 3000 BE Rotterdam")
    state, questions = dq.check_request(check, value)
    answer = judge().ask(state, questions)
    with example(quote(questions["passes"].instructions), state, questions):
        st.html(label("Jev's answer") + answers(dq_row(check, value, answer)))
        st.caption(ui.answer_caption(answer))
    st.html(
        '<div class="g-cards">'
        '<div class="g-card"><b>Noul</b>A yes/no question. One probability that the answer is yes.</div>'
        f'<div class="g-card"><b>Choice</b>Pick one of up to {schema.MAX_OPTIONS} options. '
        "A probability for every option.</div></div>"
    )
    figures(
        ("per question (median)", "~215 ms", ""),
        ("at 16 threads", "65 rows/s", ""),
        ("per million questions", "~$13", ""),
    )
    st.caption("Measured 2026-10-21 on jev-1.13.0 with scripts/measure.py (spec.md).")


def code_and_jev():
    lead(
        step().title,
        "Jev is one step in a pipeline you already own. Code finds the candidates and settles what rules can "
        "settle. Jev judges the rest. A threshold you set turns its probability into accept, review or reject.",
    )
    buckets = "".join(chip(b, c) for b, c in ui.BUCKET_COLOURS.items())
    st.html(
        '<div class="g-flow">'
        '<div class="g-node"><b>Rows</b></div><span class="g-arrow">→</span>'
        '<div class="g-node"><b>Code</b>normalize · block · exact rules · regex</div>'
        '<span class="g-arrow">→</span>'
        '<div class="g-lanes">'
        '<div class="g-lane"><small>rows the rules settle</small><span class="g-rail"></span></div>'
        '<div class="g-lane"><small>ambiguous rows</small><span class="g-arrow">→</span>'
        '<div class="g-node g-jev"><b>Jev</b>a probability</div><span class="g-arrow">→</span>'
        '<div class="g-node"><b>Thresholds</b>lo / hi, yours</div></div></div>'
        f'<span class="g-arrow">→</span><div class="g-buckets">{buckets}</div></div>'
    )
    st.table(results.STATIONS)


def dq_values():
    lead(
        step().title,
        "None of these is null or the wrong type, so type, null and range checks pass them all. "
        "Each check is one sentence in checks.yaml.",
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
        parts.append(group(f"<b>{html.escape(cid)}</b> {html.escape(check.check)}"))
        parts += [dq_row(check, v, replies[(cid, v)]) for v in examples[cid]]
    state, questions = dq.check_request(checks[shown[0]], shown[1])
    with example(quote(questions["passes"].instructions), state, questions):
        st.html(label("Jev's answer, once per distinct value") + answers(*parts))
        st.caption(ui.answer_caption(replies[shown]))


def dq_choice():
    lead(
        step().title,
        "The same idea with a Choice: map free text to a code list. When no code fits, 'other' is an answer too.",
    )
    check = dq_check("cancel_reason_code")
    values = [
        dq_value(check, v)
        for v in ("concurrent was goedkoper", "budget bevroren", "kwaliteit viel tegen")
    ]
    replies = judge().ask_many([dq.check_request(check, v) for v in values])
    parts = []
    for value, reply in zip(values, replies, strict=True):
        probabilities = reply.response.choices["code"].probabilities
        p = dq_p(check, value, reply)
        parts.append(group(f"<b>{html.escape(value)}</b>"))
        parts += [
            row(code, share)
            for code, share in sorted(probabilities.items(), key=lambda kv: -kv[1])[:2]
        ]
        parts.append(
            row(
                "p_pass = 1 − p(other)",
                p,
                [pipeline.LO, pipeline.HI],
                outcome=landing(pipeline.bucket(p), results.DQ_NAMES),
            )
        )
    state, questions = dq.check_request(check, values[-1])
    codes = "".join(
        f"<code>{html.escape(c)}</code><span>{html.escape(d)}</span>"
        for c, d in check.codes.items()
    )
    with example(
        quote(questions["code"].instructions)
        + f'<div class="g-codes two">{codes}</div>',
        state,
        questions,
    ):
        st.html(label("Jev's answer: the top two options") + answers(*parts))
        st.caption(ui.answer_caption(replies[-1]))


def dq_scale():
    judgments, first, rerun = results.dq_judgments(ui.mode())
    result = dq.run(results.ROWS, results.CHECKS, judgments, pipeline.LO, pipeline.HI)
    c = results.dq_claim(result, first, rerun)
    lead(c.headline, c.support)
    figures(
        ("Row checks", len(results.ROWS) * len(results.CHECKS), ""),
        ("Questions to Jev", first.asked, ""),
        ("Questions on tomorrow's rerun", rerun.asked, ""),
    )
    manifest = (
        pd.DataFrame(result.manifest["checks"]).T.rename_axis("check").reset_index()
    )
    static_table(
        manifest.assign(
            fail_rate=manifest["fail_rate"].map(ui.percent),
            max_fail_rate=manifest["max_fail_rate"].map(ui.percent),
            triggered=manifest["triggered"].map({True: "yes", False: ""}),
        ).rename(columns={"max_fail_rate": "limit"})
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
        height=200,
        x_title="Jev's confidence that the value passes",
        names=results.DQ_NAMES,
    )
    st.caption(
        f"One dot per distinct value. Left of {pipeline.LO:.2f} it fails, right of {pipeline.HI:.2f} it passes; "
        "in between, a person decides."
    )


def er_same_name():
    lead(
        step().title,
        "Name matching sees two identical names. Jev reads the whole record.",
    )
    ra, rb = er_pair("A02", "B02")
    state, questions = er.pair_request(ra, rb)
    answer = judge().ask(state, questions)
    with example(quote(questions["same"].instructions), state, questions):
        st.html(
            label("The two records")
            + records_table(ra, rb)
            + label("Answers")
            + er_rows(ra, rb, answer.response.nouls["same"].noul)
        )
        st.caption(ui.answer_caption(answer))


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
    for (ra, rb), reply in zip(pairs, replies, strict=True):
        names = "".join(
            f"<div><span>{r['id']}</span>{html.escape(r['name'])}</div>"
            for r in (ra, rb)
        )
        blocks.append(
            f'<div class="g-pair"><div class="g-names">{names}</div>'
            f"<div>{er_rows(ra, rb, reply.response.nouls['same'].noul)}</div></div>"
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
    c = results.er_claim(scores)
    lead(c.headline, c.support)
    figures(
        ("Possible pairs", len(results.ER_A) * len(results.ER_B), ""),
        ("After blocking", len(results.PAIRS), ""),
        ("Exact KvK/IBAN rule", len(results.EXACT), ""),
        ("Judged by Jev", len(results.AMBIGUOUS), ""),
        ("To a person", scores["Jev"]["review"], ""),
    )
    st.caption(
        "Same candidates, same exact rules. Baseline: Levenshtein similarity on normalized names, "
        f"≥ {results.BASELINE_CUTS[1]:.2f} merge, ≤ {results.BASELINE_CUTS[0]:.2f} keep separate."
    )
    compared = pd.DataFrame(scores).T.rename_axis("method").reset_index()
    static_table(
        compared.assign(
            precision=compared["precision"].map(ui.percent),
            recall=compared["recall"].map(ui.percent),
            review=compared["review"].astype(int),
            merged=compared["merged"].astype(int),
        )
    )
    names = {i: r["name"] for i, r in ER_RECORDS.items()}
    table = pd.DataFrame(matches)
    table["gold"] = [
        (x, y) in results.ER_GOLD for x, y in zip(table["id_a"], table["id_b"])
    ]
    jev_rows = table[table["by"] == "Jev"].assign(
        lane="Supplier pairs",
        pair=lambda t: t["id_a"].map(names) + " | " + t["id_b"].map(names),
    )
    ui.strip(
        jev_rows,
        "p_same",
        "lane",
        [er.LO, er.HI],
        ["pair", "p_same", "decision", "gold"],
        height=160,
        x_title="Jev's confidence that both records are the same supplier",
        names=results.ER_NAMES,
    )
    st.caption(
        f"One dot per pair that no exact KvK or IBAN rule settled. Left of {er.LO:.2f} the records "
        f"stay apart, right of {er.HI:.2f} they merge; in between, a person decides."
    )


def schema_example():
    lead(
        step().title,
        "A legacy column with no comment. Jev picks a target column from a shortlist and reads the sample values.",
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
            label("Jev's answer: the top four options")
            + source_block(source)
            + answers(*(row(option, p, [schema.CONFIDENT]) for option, p in top))
            + mapping_line(decided[source["source_col"]])
            + '<div class="g-small">'
            + source_block(second)
            + answers(row(pick["target_col"], pick["p"], [schema.CONFIDENT]))
            + mapping_line(pick)
            + "</div>"
        )
        st.caption(ui.answer_caption(answer))


def schema_scale():
    decided = results.schema_mappings(ui.mode())
    table = results.schema_table(decided)
    c = results.schema_claim(table, schema.evaluate(decided, results.SCHEMA_GOLD))
    lead(c.headline, c.support)
    st.html(label("Where Jev was wrong"))
    wrong = table[~table["correct"]]
    static_table(
        wrong.assign(
            p=wrong["p"].map("{:.2f}".format),
            reason=wrong["reason"].replace("", "pre-filled"),
        )[["source_col", "target_col", "p", "reason", "gold"]].rename(
            columns={
                "source_col": "Source column",
                "target_col": "Jev's pick",
                "reason": "Why it went to the consultant",
                "gold": "Right answer",
            }
        )
    )
    st.html(label("The output: a dbt sources.yml"))
    st.code(
        schema.sources_yml(decided, source_name="legacy_crm"),
        language=None,
        wrap_lines=True,
        height=220,
    )


def pii_example():
    lead(
        step().title,
        "Regex with checksums finds BSN, IBAN, phone and email. It can't read context.",
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
        st.html(
            label("Jev's answer: a probability per kind of data")
            + pii_bars(p)
            + verdict(route_chip(pii.route(hits, p)), before="Route")
        )
        st.caption(ui.answer_caption(answer))
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
    c = results.pii_claim(routed)
    lead(c.headline, c.support)
    counts = routed["route"].value_counts()
    figures(
        *(
            (route.capitalize(), int(counts.get(route, 0)), line)
            for route, line in ROUTE_LINES.items()
        )
    )
    with st.container(border=True):
        st.markdown("**Before client data**")
        st.write(results.GATE)


def your_turn():
    lead(
        step().title,
        "A Dutch sentence from the room. Regex runs first; if it finds nothing, Jev screens it for the five "
        "kinds of personal data.",
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
                st.caption(ui.answer_caption(answer))
    st.caption(
        "The preset answers from its recording. Anything else needs Live API calls on (sidebar)."
    )


STEPS = [
    Step(
        "System One",
        "A System One model answers a question about your data with a probability",
        "Jev is not a chatbot. One request is data plus a question in plain words, and back comes a "
        "probability. A PO box is not one building with its own house number. Two shapes of question: "
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
        "elsewhere, so Jev is unsure and a person decides.",
        dq_values,
    ),
    Step(
        "Data quality",
        "Free text to a code: a Choice",
        "Nothing in 'concurrent was goedkoper' says expensive. When no code fits, 'other' wins and the "
        "row goes to a person instead of getting a wrong code.",
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
        "square, a person decides.",
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
        "pick went to the consultant, not into the mapping. The output is a dbt sources.yml. It is below "
        "the 70% goal; most misses are abbreviations without comments.",
        schema_scale,
    ),
    Step(
        "PII screening",
        "What regex can't see",
        "Regex can't see that a neighbour with diabetes is health data about a private person. Five "
        "yes/no questions in one request. Trade-union membership is special-category data; a public "
        "official is not a private person.",
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

with st.sidebar:
    st.subheader("Speaker note")
    st.write(step().note)
    if n < len(STEPS):
        st.caption(f"Next: {STEPS[n].title}")
    # A new step should open at its top. The snippet sits here, at a position that doesn't depend on
    # the step's body, and carries the step number: the element only changes when the step does, so a
    # rerun on the same step ("Ask Jev", a sidebar toggle) leaves the scroll alone.
    st.html(
        f"<script>/* step {n} */ document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, 0);</script>",
        unsafe_allow_javascript=True,
    )
