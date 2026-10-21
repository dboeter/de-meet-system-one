import pandas as pd
import streamlit as st

import ui
from jevdemo import er
from jevdemo.judge import LiveUnavailable, NotRecorded
from jevdemo.pipeline import bucket

finding = ui.header("Entity resolution: one supplier, two records", "02_entity.ipynb")

a, b, gold = er.load_table("a"), er.load_table("b"), er.load_gold()
pairs = er.candidate_pairs(a, b)
exact = [(ra, rb) for ra, rb in pairs if er.exact_match(ra, rb)]
ambiguous = [(ra, rb) for ra, rb in pairs if not er.exact_match(ra, rb)]
names = {r["id"]: r["name"] for r in a + b}


@st.cache_data(show_spinner="Asking Jev…")
def judge_pairs(mode: str) -> dict[tuple[str, str], float]:
    answers = ui.judge(mode).ask_many([er.pair_request(ra, rb) for ra, rb in ambiguous])
    return {
        (ra["id"], rb["id"]): ans.response.nouls["same"].noul
        for (ra, rb), ans in zip(ambiguous, answers, strict=True)
    }


p_same = judge_pairs(ui.mode())

left, right = st.columns([1, 2], gap="large")
with left:
    lo, hi = st.slider(
        "Thresholds on p_same (keep separate ≤ lo, merge ≥ hi)",
        0.0,
        1.0,
        (er.LO, er.HI),
        0.01,
        help="Chosen on this same small set, no holdout. Moving them makes no API calls.",
    )

matches = [
    {
        "id_a": ra["id"],
        "id_b": rb["id"],
        "p_same": 1.0,
        "decision": "accept",
        "by": "exact rule",
    }
    for ra, rb in exact
] + [
    {"id_a": x, "id_b": y, "p_same": p, "decision": bucket(p, lo, hi), "by": "Jev"}
    for (x, y), p in p_same.items()
]
table = pd.DataFrame(matches)
table.insert(2, "name_a", table["id_a"].map(names))
table.insert(3, "name_b", table["id_b"].map(names))
table["gold"] = [(x, y) in gold for x, y in zip(table["id_a"], table["id_b"])]

jev = {(m["id_a"], m["id_b"]): m["decision"] for m in matches}
fuzzy = {
    (ra["id"], rb["id"]): "accept"
    if er.exact_match(ra, rb)
    else bucket(er.name_similarity(ra, rb), 0.50, 0.85)
    for ra, rb in pairs
}
scores = {"Levenshtein": er.evaluate(fuzzy, gold), "Jev": er.evaluate(jev, gold)}
j, f = scores["Jev"], scores["Levenshtein"]
finding.markdown(
    f"**Jev merges {j['merged']} pairs at {ui.percent(j['precision'])} precision, "
    f"{ui.percent(j['recall'])} recall, {j['review']} to review.** "
    f"Levenshtein on the same candidates: {ui.percent(f['precision'])} precision, "
    f"{ui.percent(f['recall'])} recall, {f['review']} to review."
)

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
with right:
    jev_rows = table[table["by"] == "Jev"].assign(
        lane="Jev pairs", pair=lambda t: t["name_a"] + " | " + t["name_b"]
    )
    ui.strip(
        jev_rows,
        "p_same",
        "lane",
        [lo, hi],
        ["pair", "p_same", "decision", "gold"],
        height=160,
    )

st.subheader("Jev against the fuzzy-match baseline")
st.caption(
    "Same candidates, same exact rules. Baseline: Levenshtein similarity on normalized names, ≥ 0.85 merge, ≤ 0.50 keep separate."
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
        st.metric(f"p_same → {bucket(p, lo, hi)}", f"{p:.2f}")
        st.caption(ui.answer_caption(answer))
    except (NotRecorded, LiveUnavailable) as e:
        st.warning(str(e))
