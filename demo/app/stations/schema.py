import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import schema
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("Schema mapping for a migration")

sources, targets, gold = results.SOURCES, results.TARGETS, results.SCHEMA_GOLD
decided = results.schema_mappings(ui.mode())
scores = schema.evaluate(decided, gold)
table = results.schema_table(decided)
ui.claim(finding, results.schema_claim(table))

left, chart = st.columns([1, 2], gap="large")
with left:
    c1, c2 = st.columns(2)
    c1.metric(
        "Accept",
        int((table["decision"] == "accept").sum()),
        help=f"of {len(table)} source columns",
    )
    c2.metric("Review", int((table["decision"] == "review").sum()))
    c1.metric("Top-1 accuracy", ui.percent(scores["top1_accuracy"]))
    c2.metric(
        "None right",
        ui.percent(scores["none_accuracy"]),
        help="Columns with no target equivalent",
    )
with chart:
    ui.strip(
        table.assign(
            outcome=lambda t: t["correct"].map(
                {True: "Right column", False: "Wrong column"}
            )
        ),
        "p",
        "outcome",
        [schema.CONFIDENT],
        ["source_col", "target_col", "gold", "p", "reason"],
        x_title="Probability",
        title="How sure was Jev of the column it picked?",
        subtitle=(
            f"One dot per source column. Right of {schema.CONFIDENT:.2f} accept, "
            "unless another column took the target."
        ),
    )


def your_turn():
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
            st.warning(
                f"Unknown source table: {e}" if isinstance(e, KeyError) else str(e)
            )


shown = (
    table.assign(target_col=list(map(ui.marked, table["target_col"], table["correct"])))
    .drop(columns="correct")
    .rename(columns={"gold": "right answer"})
)
with st.expander("Details"):
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
        st.dataframe(shown, hide_index=True, column_config={"p": ui.P_COLUMN})
    with wrong:
        st.caption(
            "A wrong answer in review costs a minute. A wrong answer that was accepted is the expensive kind."
        )
        st.dataframe(
            shown[~table["correct"]], hide_index=True, column_config={"p": ui.P_COLUMN}
        )
    with yml:
        st.caption("Only accepted mappings; review rows are left out.")
        st.code(
            schema.sources_yml(decided, source_name="legacy_crm"),
            language=None,
            wrap_lines=True,
        )
    with tried:
        st.markdown(
            "- **Current:** `none` as one of the Choice options, no `(type)` suffix on option descriptions, "
            "the source system in state. 80% top-1, 64% of columns pre-filled correctly.\n"
            "- **As first specified** (type suffix, no source system): 76% top-1, 60% pre-filled, one wrong pre-fill.\n"
            "- Adding generic context to the question: 64% pre-filled correctly.\n"
            "- Replacing the `none` option with a companion Noul: 36%, because the Noul was under-confident on most columns.\n"
            "\n"
            "The errors are mostly Dutch abbreviations without comments (`VRZ`, `BTW`); "
            "a consultant's abbreviation list is the obvious next lever."
        )
    with data:
        st.dataframe(pd.DataFrame(sources), hide_index=True)
        st.dataframe(pd.DataFrame(targets), hide_index=True)

example = next(s for s in sources if s["source_col"] == "KLANT.KLT_NM_VOL")
ui.request_view(*schema.mapping_request(example, targets))

your_turn()
