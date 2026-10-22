"""The question-wording experiments as data and charts, shared by notebook 05 and the app's lessons page."""

from functools import partial

import altair as alt
import pandas as pd

from jevdemo import dq, schema
from jevdemo.pipeline import HI, LO

# The app's ledger style: ink chrome, one blue on data, red only where harm is done.
INK, GREY, BLUE, RED = "#141414", "#8a8a8a", "#1d5fbf", "#c4242a"
LANE = "#f2f4f7"

# Each run: how to ask for one source column, and how to read the answer.
SCHEMA_RUNS = {
    **{
        name: (
            partial(schema.mapping_request, **schema.VARIANTS[variant]),
            schema.to_mapping,
        )
        for name, variant in {
            "First version": "type_no_context",
            "No type suffix": "no_type_no_context",
            "Source system in state": "type_context",
            "Both (now the default)": "default",
        }.items()
    },
    "Yes/no per target": (schema.bool_mapping_request, schema.to_mapping_bool),
}
# Ordered from best to worst outcome, so the legend reads as a scale.
OUTCOMES = {
    "Pre-filled, right": BLUE,
    "To review, right pick": "#a9c1e8",
    "To review, wrong pick": "#d9d9d9",
    "Pre-filled, wrong": RED,
}

WORDINGS = {
    "address_is_postal": ("Address", "Before: street + number", "Now: one building, its own number"),
    "cancel_reason_code": ("Cancel reason", "Tried: Noul + Choice", "Now: 1 − p(other)"),
}  # fmt: skip
LABELS = {
    "address_is_postal": lambda r: r["is_address"],
    "cancel_reason_code": lambda r: r["cancel_code"] != "other",
}


def schema_outcomes(judge) -> pd.DataFrame:
    """One row per (run, source column): what was picked and where it landed."""
    sources, targets, gold = (
        schema.load_sources(),
        schema.load_targets(),
        schema.load_gold(),
    )
    frames = []
    for run, (ask, read) in SCHEMA_RUNS.items():
        answers = judge.ask_many([ask(s, targets) for s in sources])
        decided = schema.decide([read(s, a.response) for s, a in zip(sources, answers)])
        for order, m in enumerate(decided):
            right = m["target_col"] == gold[m["source_col"]]
            prefilled = m["decision"] == "accept"
            outcome = (
                ("Pre-filled, right" if right else "Pre-filled, wrong")
                if prefilled
                else ("To review, right pick" if right else "To review, wrong pick")
            )
            frames.append(
                {
                    "run": run,
                    "order": order,
                    "source_col": m["source_col"],
                    "picked": m["target_col"],
                    "gold": gold[m["source_col"]],
                    "p": round(m["p"], 2),
                    "outcome": outcome,
                }
            )
    return pd.DataFrame(frames)


def dq_margins(judge) -> pd.DataFrame:
    """One row per (check, wording, data row): p_pass and the hand label."""
    rows = dq.load_rows()
    frames = []
    for path, which in ((dq.CHECK_VARIANTS, 1), (dq.CHECKS, 2)):
        checks = [c for c in dq.load_checks(path) if c.id in WORDINGS]
        judged, _ = dq.judge_checks(
            rows, checks, judge, dq.Cache()
        )  # fresh cache: ids repeat
        p = {(j.check_id, j.value): j.p_pass for j in judged}
        for c in checks:
            for r in rows:
                frames.append(
                    {
                        "check": WORDINGS[c.id][0],
                        "wording": WORDINGS[c.id][which],
                        "value": r[c.column],
                        "p_pass": round(p[c.id, r[c.column]], 2),
                        "label": "Labelled pass"
                        if LABELS[c.id](r)
                        else "Labelled fail",
                    }
                )
    return pd.DataFrame(frames)


def _ledger(chart, symbol: str):
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            grid=False,
            domain=False,
            ticks=False,
            labelColor="#3d3d3d",
            titleColor="#3d3d3d",
            labelFontSize=12,
            titleFontSize=12,
            labelLimit=260,
        )
        .configure_legend(
            labelColor="#3d3d3d",
            labelFontSize=12,
            titleFontSize=12,
            symbolType=symbol,
            orient="top",
            title=None,
        )
        .configure_title(fontSize=14, fontWeight=600, anchor="start", color=INK)
    )


def outcome_grid(outcomes: pd.DataFrame):
    """Each square is one source column, in the same place in every run, so a change shows as a column that flips."""
    runs = list(SCHEMA_RUNS)
    y = alt.Y("run:N", sort=runs, title=None, axis=alt.Axis(labelPadding=10))
    squares = (
        alt.Chart(outcomes)
        .mark_square(size=230, opacity=1)
        .encode(
            x=alt.X(
                "order:O",
                title="Source columns, same order in every run",
                axis=alt.Axis(labels=False),
            ),
            y=y,
            color=alt.Color(
                "outcome:N",
                sort=list(OUTCOMES),
                scale=alt.Scale(domain=list(OUTCOMES), range=list(OUTCOMES.values())),
            ),
            tooltip=["source_col", "picked", "gold", "p", "outcome"],
        )
        .properties(width=alt.Step(17))
    )
    totals = (
        outcomes.assign(
            right=outcomes["outcome"] == "Pre-filled, right",
            wrong=outcomes["outcome"] == "Pre-filled, wrong",
        )
        .groupby("run", as_index=False)[["right", "wrong"]]
        .sum()
    )
    totals["text"] = [
        f"{r} of {len(outcomes) // len(runs)} pre-filled right"
        + (f", {w} wrong" if w else "")
        for r, w in zip(totals["right"], totals["wrong"])
    ]
    text = (
        alt.Chart(totals)
        .mark_text(align="left", fontSize=12, color=INK)
        .encode(x=alt.value(0), y=alt.Y("run:N", sort=runs, axis=None), text="text:N")
        .properties(width=180)
    )
    return _ledger(alt.hconcat(squares, text, spacing=16), symbol="square")


def margin_strips(margins: pd.DataFrame):
    """p_pass per row on 0..1; a good wording leaves the grey review band empty."""
    charts = []
    for check, frame in margins.groupby("check", sort=False):
        lanes = list(dict.fromkeys(frame["wording"]))
        # Padding keeps the jitter of the two lanes apart.
        y = alt.Y(
            "wording:N",
            sort=lanes,
            title=None,
            axis=alt.Axis(minExtent=230, labelPadding=14),
            scale=alt.Scale(paddingInner=0.4, paddingOuter=0.2),
        )
        in_band = frame[(frame["p_pass"] > LO) & (frame["p_pass"] < HI)]
        counts = in_band.groupby("wording").size().reindex(lanes, fill_value=0)
        band = (
            alt.Chart(pd.DataFrame({"lo": [LO], "hi": [HI]}))
            .mark_rect(color=LANE)
            .encode(x="lo:Q", x2="hi:Q")
        )
        count = (
            alt.Chart(pd.DataFrame({"wording": lanes, "n": counts.to_list()}))
            .transform_calculate(text="datum.n + ' to review'")
            .mark_text(fontSize=12, color=GREY)
            .encode(x=alt.datum((LO + HI) / 2), y=y, text="text:N")
        )
        dots = (
            alt.Chart(frame)
            .transform_calculate(jitter="random()")
            .mark_circle(size=60, opacity=0.85)
            .encode(
                x=alt.X("p_pass:Q", scale=alt.Scale(domain=[0, 1]), title="p(pass)"),
                y=y,
                yOffset=alt.YOffset("jitter:Q"),
                color=alt.Color(
                    "label:N",
                    scale=alt.Scale(
                        domain=["Labelled pass", "Labelled fail"], range=[BLUE, INK]
                    ),
                ),
                tooltip=["value", "p_pass", "label"],
            )
        )
        charts.append(
            alt.layer(band, count, dots).properties(title=check, width=520, height=130)
        )
    return _ledger(alt.vconcat(*charts, spacing=24), symbol="circle")


def yes_scores(judge) -> pd.DataFrame:
    """The yes/no run's p(yes) for every shortlisted target of the columns that have one in gold."""
    sources, targets, gold = (
        schema.load_sources(),
        schema.load_targets(),
        schema.load_gold(),
    )
    answers = judge.ask_many([schema.bool_mapping_request(s, targets) for s in sources])
    return pd.DataFrame(
        {
            "source_col": s["source_col"],
            "target": target,
            "p_yes": round(answer.noul, 2),
            "lane": "Gold target"
            if target == gold[s["source_col"]]
            else "Other targets",
        }
        for s, a in zip(sources, answers)
        if gold[s["source_col"]] != schema.NONE
        for target, answer in a.response.nouls.items()
    )


def yes_strips(scores: pd.DataFrame):
    """Right target, low confidence: most gold targets land just under the pre-fill cutoff."""
    above = scores[scores["p_yes"] >= schema.CONFIDENT].groupby("lane").size()
    totals = scores.groupby("lane").size()
    names = {
        lane: f"{lane}: {above.get(lane, 0)} of {totals[lane]} reach it"
        for lane in ("Gold target", "Other targets")
    }
    scores = scores.assign(lane=scores["lane"].map(names))
    lanes = list(names.values())
    y = alt.Y(
        "lane:N",
        sort=lanes,
        title=None,
        axis=alt.Axis(minExtent=230, labelPadding=14),
        scale=alt.Scale(paddingInner=0.4, paddingOuter=0.2),
    )
    rule = alt.Chart(pd.DataFrame({"x": [schema.CONFIDENT]})).encode(x="x:Q")
    cutoff = rule.mark_rule(color=INK, strokeDash=[4, 3]) + rule.mark_text(
        text=f"pre-fill cutoff {schema.CONFIDENT:.2f}",
        align="right",
        dx=-6,
        y=-8,
        fontSize=12,
        color=INK,
    )
    dots = (
        alt.Chart(scores)
        .transform_calculate(jitter="random()")
        .mark_circle(size=60, opacity=0.85)
        .encode(
            x=alt.X("p_yes:Q", scale=alt.Scale(domain=[0, 1]), title="p(yes)"),
            y=y,
            yOffset=alt.YOffset("jitter:Q"),
            color=alt.Color(
                "lane:N", scale=alt.Scale(domain=lanes, range=[BLUE, GREY]), legend=None
            ),
            tooltip=["source_col", "target", "p_yes"],
        )
    )
    return _ledger(
        alt.layer(cutoff, dots).properties(width=520, height=130), symbol="circle"
    )
