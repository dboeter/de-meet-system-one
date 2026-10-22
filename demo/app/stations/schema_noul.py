import pandas as pd
import streamlit as st

import ui
from jevdemo import schema
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("Schema mapping, one yes/no per option", "03_schema.ipynb")

sources, targets, gold = (
    schema.load_sources(),
    schema.load_targets(),
    schema.load_gold(),
)
shortlists = {s["source_col"]: schema.shortlist(s, targets) for s in sources}


@st.cache_data(show_spinner="Asking Jev…")
def map_columns(
    mode: str,
) -> tuple[list[dict], list[dict], dict[str, dict[str, float]]]:
    """Choice mappings, Noul mappings, and every Noul's p(yes) per source column."""
    judge = ui.judge(mode)
    choice = judge.ask_many([schema.mapping_request(s, targets) for s in sources])
    noul = judge.ask_many([schema.bool_mapping_request(s, targets) for s in sources])
    return (
        [
            {
                **schema.to_mapping(s, a.response),
                "shortlist": shortlists[s["source_col"]],
            }
            for s, a in zip(sources, choice, strict=True)
        ],
        [
            {
                **schema.to_mapping_bool(s, a.response),
                "shortlist": shortlists[s["source_col"]],
            }
            for s, a in zip(sources, noul, strict=True)
        ],
        {
            s["source_col"]: {t: n.noul for t, n in a.response.nouls.items()}
            for s, a in zip(sources, noul, strict=True)
        },
    )


choice_mappings, noul_mappings, p_yes = map_columns(ui.mode())
decided = schema.decide(noul_mappings)
scores = schema.evaluate(decided, gold)
choice_scores = schema.evaluate(schema.decide(choice_mappings), gold)
table = pd.DataFrame(decided)[["source_col", "target_col", "p", "decision", "reason"]]
table["gold"] = table["source_col"].map(gold)
table["correct"] = table["target_col"] == table["gold"]

mapped = [c for c in p_yes if gold[c] != schema.NONE]
strongest_right = sum(max(p_yes[c], key=p_yes[c].get) == gold[c] for c in mapped)
gold_p = pd.Series([p_yes[c][gold[c]] for c in mapped])

finding.markdown(
    f"**{ui.percent(scores['prefilled_correct'])} of columns pre-filled correctly, against "
    f"{ui.percent(choice_scores['prefilled_correct'])} with a Choice.** The ranking is good: the "
    f"strongest yes is the gold target for {strongest_right} of {len(mapped)} mapped columns. "
    f"But p(yes) runs low (gold targets median {gold_p.median():.2f}), so most columns fall "
    f"below {schema.CONFIDENT:.2f} and map to `none`."
)

left, right = st.columns([1, 2], gap="large")
with left:
    c1, c2 = st.columns(2)

    def delta(key: str) -> str:
        return f"{scores[key] - choice_scores[key]:+.0%} vs Choice"

    c1.metric(
        "Pre-filled correct",
        ui.percent(scores["prefilled_correct"]),
        delta("prefilled_correct"),
    )
    c2.metric(
        "Top-1 accuracy", ui.percent(scores["top1_accuracy"]), delta("top1_accuracy")
    )
    c1.metric(
        "None right",
        ui.percent(scores["none_accuracy"]),
        delta("none_accuracy"),
        help="Columns with no target equivalent",
    )
    c2.metric(
        "Strongest yes right",
        f"{strongest_right} of {len(mapped)}",
        help="Ignoring the threshold, over columns that have a gold target",
    )
    st.caption(
        f"One Noul per shortlisted target, no `none` option. A column maps to `none` when no "
        f"target reaches p(yes) ≥ {schema.CONFIDENT:.2f}, with p = 1 − the strongest yes; "
        "more than one target above it goes to review."
    )
with right:
    ui.strip(
        pd.DataFrame(
            [
                {
                    "source_col": c,
                    "target_col": t,
                    "p(yes)": p,
                    "target": "gold" if t == gold[c] else "other",
                }
                for c in mapped
                for t, p in p_yes[c].items()
            ]
        ),
        "p(yes)",
        "target",
        [schema.CONFIDENT],
        ["source_col", "target_col", "p(yes)"],
        colour=None,
        height=180,
    )

mapping, compare, tried = st.tabs(
    ["Mapping table", "Against the Choice", "What we tried"]
)
with mapping:
    st.dataframe(table, hide_index=True, column_config={"p": ui.P_COLUMN})
with compare:
    st.dataframe(
        pd.DataFrame({"choice": choice_scores, "noul": scores}).round(2),
        column_config={"choice": ui.P_COLUMN, "noul": ui.P_COLUMN},
    )
    st.dataframe(
        pd.DataFrame(
            {
                "source_col": [m["source_col"] for m in choice_mappings],
                "gold": [gold[m["source_col"]] for m in choice_mappings],
                "choice": [m["target_col"] for m in choice_mappings],
                "noul": [m["target_col"] for m in noul_mappings],
            }
        ),
        hide_index=True,
    )
with tried:
    st.markdown(
        "- Same shortlist and source description as the Choice page; each target is asked "
        '"Does `source_column` hold the same data as the target column …?"\n'
        "- Scores are independent: a single-question request gives the same p(yes) as the batched one.\n"
        "- The same under-confidence sank the companion-Noul attempt on the Choice page (36%). "
        "We didn't tune a lower cutoff on these 25 columns; that would fit the test set."
    )

example = next(s for s in sources if s["source_col"] == "KLANT.KLT_NM_VOL")
ui.request_view(*schema.bool_mapping_request(example, targets))

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
        answer = ui.judge(ui.mode()).ask(*schema.bool_mapping_request(column, targets))
        m = schema.to_mapping_bool(column, answer.response)
        st.metric(f"{m['source_col']} →", m["target_col"])
        st.caption(f"p = {m['p']:.2f} · {ui.answer_caption(answer)}")
        st.dataframe(
            pd.Series(
                {t: n.noul for t, n in answer.response.nouls.items()}, name="p(yes)"
            ).sort_values(ascending=False),
            column_config={"p(yes)": ui.P_COLUMN},
        )
    except (NotRecorded, LiveUnavailable, KeyError) as e:
        st.warning(f"Unknown source table: {e}" if isinstance(e, KeyError) else str(e))
