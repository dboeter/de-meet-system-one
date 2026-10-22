import pandas as pd
import streamlit as st

import ui
from jevdemo import schema
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("Schema mapping for a migration", "03_schema.ipynb")

sources, targets, gold = (
    schema.load_sources(),
    schema.load_targets(),
    schema.load_gold(),
)
shortlists = {s["source_col"]: schema.shortlist(s, targets) for s in sources}


@st.cache_data(show_spinner="Asking Jev…")
def map_columns(mode: str) -> list[dict]:
    answers = ui.judge(mode).ask_many(
        [schema.mapping_request(s, targets) for s in sources]
    )
    return [
        {**schema.to_mapping(s, a.response), "shortlist": shortlists[s["source_col"]]}
        for s, a in zip(sources, answers, strict=True)
    ]


decided = schema.decide(map_columns(ui.mode()))
scores = schema.evaluate(decided, gold)
table = pd.DataFrame(decided)[["source_col", "target_col", "p", "decision", "reason"]]
table["gold"] = table["source_col"].map(gold)
table["correct"] = table["target_col"] == table["gold"]
wrong_prefilled = table[~table["correct"] & (table["decision"] == "accept")]

finding.markdown(
    f"**{ui.percent(scores['prefilled_correct'])} of columns pre-filled correctly, "
    f"{ui.percent(scores['top1_accuracy'])} top-1; the target was 70%.** "
    + (
        f"{len(wrong_prefilled)} wrong mapping pre-filled: "
        + ", ".join(
            f"{r.source_col} → {r.target_col} at {r.p:.2f}"
            for r in wrong_prefilled.itertuples()
        )
        + ". This is why a person approves the file."
        if len(wrong_prefilled)
        else "No wrong mapping was pre-filled."
    )
)

left, right = st.columns([1, 2], gap="large")
with left:
    c1, c2 = st.columns(2)
    c1.metric(
        "Pre-filled",
        int((table["decision"] == "accept").sum()),
        help=f"of {len(table)} source columns",
    )
    c2.metric("To the consultant", int((table["decision"] == "review").sum()))
    c1.metric("Top-1 accuracy", ui.percent(scores["top1_accuracy"]))
    c2.metric(
        "None right",
        ui.percent(scores["none_accuracy"]),
        help="Columns with no target equivalent",
    )
    st.caption(
        f"Pre-filled when p ≥ {schema.CONFIDENT:.2f} and no other column claims the same 1:1 target. "
        f"Shortlists hold {min(map(len, shortlists.values()))}–{max(map(len, shortlists.values()))} options; "
        f"shortlist recall {ui.percent(scores['shortlist_recall'])} by construction."
    )
with right:
    ui.strip(
        table.assign(
            outcome=lambda t: t["correct"].map({True: "correct", False: "wrong"})
        ),
        "p",
        "outcome",
        [schema.CONFIDENT],
        ["source_col", "target_col", "gold", "p", "reason"],
        height=180,
    )

mapping, wrong, yml, tried, data = st.tabs(
    [
        "Mapping table",
        "Where it went wrong",
        "dbt sources.yml",
        "What we tried",
        "Source and target",
    ]
)
with mapping:
    st.dataframe(table, hide_index=True, column_config={"p": ui.P_COLUMN})
with wrong:
    st.caption(
        "A wrong answer in review costs the consultant a minute. A wrong answer that was pre-filled is the expensive kind."
    )
    st.dataframe(
        table[~table["correct"]], hide_index=True, column_config={"p": ui.P_COLUMN}
    )
with yml:
    st.caption("Only pre-filled mappings; the review rows go to the consultant's list.")
    st.code(
        schema.sources_yml(decided, source_name="legacy_crm"),
        language=None,
        wrap_lines=True,
    )
with tried:
    st.markdown(
        "- **As specified:** `none` as one of the Choice options. 76% top-1, 60% of columns pre-filled correctly.\n"
        "- Adding generic context to the question: 64% pre-filled correctly.\n"
        "- Replacing the `none` option with a companion Noul: 36%, because the Noul was under-confident on most columns.\n"
        "- One Noul per option instead of a Choice: 24%. The strongest yes is right for 18 of 22 mapped columns, "
        "but p(yes) rarely reaches 0.80 (see *Schema mapping (yes/no)*).\n\n"
        "The errors are mostly Dutch abbreviations without comments (`LVR`, `VRZ`, `BTW`); "
        "a consultant's abbreviation list is the obvious next lever."
    )
with data:
    st.dataframe(pd.DataFrame(sources), hide_index=True)
    st.dataframe(pd.DataFrame(targets), hide_index=True)

example = next(s for s in sources if s["source_col"] == "KLANT.KLT_NM_VOL")
ui.request_view(*schema.mapping_request(example, targets))

st.subheader("Your turn")
preset = schema.LIVE_PRESET
with st.form("live"):
    c1, c2 = st.columns(2)
    name = c1.text_input(
        "Column (TABLE.COLUMN, table KLANT or ORDER)", preset["source_col"]
    )
    kind = c2.text_input("Type", preset["type"])
    comment = c1.text_input("Comment", preset["comment"])
    samples = c2.text_input(
        "Sample values, separated by |", "|".join(preset["samples"])
    )
    asked = st.form_submit_button("Ask Jev", type="primary")
if asked:
    column = {
        "source_col": name,
        "type": kind,
        "comment": comment,
        "samples": samples.split("|"),
    }
    try:
        answer = ui.judge(ui.mode()).ask(*schema.mapping_request(column, targets))
        m = schema.to_mapping(column, answer.response)
        st.metric(f"{m['source_col']} →", m["target_col"])
        st.caption(f"p = {m['p']:.2f} · {ui.answer_caption(answer)}")
    except (NotRecorded, LiveUnavailable, KeyError) as e:
        st.warning(f"Unknown source table: {e}" if isinstance(e, KeyError) else str(e))
