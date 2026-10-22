import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import er
from jevdemo.judge import LiveUnavailable, NotRecorded
from jevdemo.pipeline import bucket

finding = ui.header("Entity resolution: one supplier, two records")

a, b, gold = results.ER_A, results.ER_B, results.ER_GOLD
pairs, exact, ambiguous = results.PAIRS, results.EXACT, results.AMBIGUOUS
names = {r["id"]: r["name"] for r in a + b}
p_same = results.er_p_same(ui.mode())

left, chart = st.columns([1, 2], gap="large")
with left:
    lo, hi = st.slider(
        "Thresholds (reject below, accept above)",
        0.0,
        1.0,
        (er.LO, er.HI),
        0.01,
        help="Moving them makes no API calls.",
    )

matches = results.er_matches(p_same, lo, hi)
table = pd.DataFrame(matches)
table.insert(2, "name_a", table["id_a"].map(names))
table.insert(3, "name_b", table["id_b"].map(names))
table["gold"] = [(x, y) in gold for x, y in zip(table["id_a"], table["id_b"])]

jev = {(m["id_a"], m["id_b"]): m["decision"] for m in matches}
fuzzy = results.er_baseline()
scores = {"Levenshtein": er.evaluate(fuzzy, gold), "Jev": er.evaluate(jev, gold)}
j = scores["Jev"]
ui.claim(finding, results.er_claim(scores))

with left:
    c1, c2 = st.columns(2)
    c1.metric(
        "Candidate pairs",
        len(pairs),
        help=f"of {len(a)} × {len(b)} = {len(a) * len(b)} possible",
    )
    c2.metric("Settled by exact rule", len(exact), help="Same KvK or IBAN")
    c1.metric("Judged by Jev", len(ambiguous))
    c2.metric("Review queue", j["review"])
    seen = {(ra["id"], rb["id"]) for ra, rb in pairs}
    st.caption(
        f"Blocking recall: {len(seen & gold)} of {len(gold)} gold pairs reach a candidate. "
        "Jev can't match a pair it never sees."
    )
with chart:
    jev_rows = table[table["by"] == "Jev"].assign(
        lane="Supplier pairs", pair=lambda t: t["name_a"] + " | " + t["name_b"]
    )
    ui.strip(
        jev_rows,
        "p_same",
        "lane",
        [lo, hi],
        ["pair", "p_same", "decision", "gold"],
        height=160,
        x_title="Jev's confidence that both records are the same supplier",
    )
    st.caption(
        f"One dot per pair that no exact KvK or IBAN rule settled. Left of {lo:.2f} the records "
        f"are rejected, right of {hi:.2f} accepted; in between, review."
    )


def your_turn():
    st.subheader("Your turn")
    fields = ["name", "street", "postcode", "city", "kvk", "iban"]
    with st.form("live"):
        cols = st.columns(2)
        records = []
        for col, preset in zip(cols, er.LIVE_PRESET, strict=True):
            with col:
                st.markdown(f"Record {preset['id']}")
                records.append(
                    {
                        "id": preset["id"],
                        **{
                            k: st.text_input(k, preset[k], key=f"{preset['id']}-{k}")
                            for k in fields
                        },
                    }
                )
        asked = st.form_submit_button("Ask Jev", type="primary")
    if asked:
        try:
            answer = ui.judge(ui.mode()).ask(*er.pair_request(*records))
            p = answer.response.nouls["same"].noul
            st.metric(bucket(p, lo, hi).capitalize(), f"{p:.2f}")
            st.caption(ui.answer_caption(answer))
        except (NotRecorded, LiveUnavailable) as e:
            st.warning(str(e))


st.subheader("Jev against the fuzzy-match baseline")
st.caption(
    "Same candidates, same exact rules. Baseline: Levenshtein similarity on normalized names, "
    f"≥ {results.BASELINE_CUTS[1]:.2f} accept, ≤ {results.BASELINE_CUTS[0]:.2f} reject."
)
st.dataframe(
    pd.DataFrame(scores).T.rename_axis("method").reset_index(),
    hide_index=True,
    column_config={
        "precision": st.column_config.NumberColumn(format="percent"),
        "recall": st.column_config.NumberColumn(format="percent"),
    },
)

matched, disagree, clustered, tables = st.tabs(
    ["Match table", "Where they disagree", "Clusters", "Source tables"]
)
with matched:
    st.dataframe(
        table.sort_values("p_same", ascending=False),
        hide_index=True,
        column_config={"p_same": ui.P_COLUMN},
    )
with disagree:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "pair": f"{names[x]} | {names[y]}",
                    "gold": (x, y) in gold,
                    "Levenshtein": fuzzy[(x, y)],
                    "Jev": jev[(x, y)],
                }
                for x, y in jev
                if fuzzy[(x, y)] != jev[(x, y)]
            ],
            columns=["pair", "gold", "Levenshtein", "Jev"],
        ),
        hide_index=True,
    )
with clustered:
    st.caption("Union-find over the merges gives every record a cluster id.")
    cluster_of = er.clusters(
        [r["id"] for r in a + b],
        [(m["id_a"], m["id_b"]) for m in matches if m["decision"] == "accept"],
    )
    grouped = pd.DataFrame(
        [{"cluster": c, "id": i, "name": names[i]} for i, c in cluster_of.items()]
    )
    st.dataframe(
        grouped[grouped.duplicated("cluster", keep=False)].sort_values(
            ["cluster", "id"]
        ),
        hide_index=True,
    )
with tables:
    ta, tb = st.columns(2)
    ta.dataframe(pd.DataFrame(a), hide_index=True)
    tb.dataframe(pd.DataFrame(b), hide_index=True)

jansen = next(p for p in ambiguous if p[0]["id"] == "A02")
ui.request_view(*er.pair_request(*jansen))

your_turn()
