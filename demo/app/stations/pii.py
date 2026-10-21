import pandas as pd
import streamlit as st

import ui
from jevdemo import pii
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("PII screening of free text", "04_pii.ipynb")

notes = pii.load_notes()
hits = {n["id"]: pii.regex_hits(n["text"]) for n in notes}
rest = [n for n in notes if not hits[n["id"]]]


@st.cache_data(show_spinner="Asking Jev…")
def screen(mode: str) -> dict[str, dict[str, float]]:
    answers = ui.judge(mode).ask_many([pii.screen_request(n["text"]) for n in rest])
    return {
        n["id"]: {c: a.response.nouls[c].noul for c in pii.CATEGORIES}
        for n, a in zip(rest, answers, strict=True)
    }


probs = screen(ui.mode())
routed = pd.DataFrame(
    [
        {
            "id": n["id"],
            "text": n["text"],
            "regex": ", ".join(sorted(hits[n["id"]])),
            "route": pii.route(hits[n["id"]], probs.get(n["id"], {})),
        }
        for n in notes
    ]
)
routes = routed["route"].value_counts()
contextual = [n for n in notes if any(n[c] for c in pii.CATEGORIES)]
by_regex = sum(bool(hits[n["id"]]) for n in contextual)
by_jev = sum(
    routed.set_index("id").loc[n["id"], "route"] != "clear" for n in contextual
)

finding.markdown(
    f"**Notes with contextual PII: {len(contextual)}. Regex caught {by_regex}; regex + Jev caught {by_jev}.** "
    f"{routes.get('excluded', 0)} notes are excluded from gold as health or Art. 9 data."
)

left, right = st.columns([1, 2], gap="large")
with left:
    c1, c2 = st.columns(2)
    for col, name in zip(
        [c1, c2, c1, c2], ["excluded", "restricted", "masked", "clear"], strict=True
    ):
        col.metric(name.capitalize(), int(routes.get(name, 0)))
    st.caption(
        f"{len(notes)} notes: regex with checksums settled {len(notes) - len(rest)}, Jev screened {len(rest)}. "
        f"A category counts at p ≥ {pii.THRESHOLD:.2f}, low on purpose: a missed flag costs more than a review."
    )
with right:
    long = pd.DataFrame(
        [
            {
                "id": i,
                "category": c,
                "p": p,
                "text": next(n["text"] for n in rest if n["id"] == i),
            }
            for i, ps in probs.items()
            for c, p in ps.items()
        ]
    )
    ui.strip(
        long,
        "p",
        "category",
        [pii.THRESHOLD],
        ["id", "text", "p"],
        colour=None,
        height=260,
    )

route_tab, cats, extra, regex = st.tabs(
    ["Routing", "Per category", "Flagged beyond our labels", "Regex hits"]
)
with route_tab:
    st.caption(
        "Health and Art. 9 → excluded from gold. Other categories Jev finds → restricted, because Jev says "
        "whether, not where. Regex hits → masked, because code knows the span."
    )
    st.dataframe(routed, hide_index=True)
with cats:
    rows = []
    for c in pii.CATEGORIES:
        flagged = {i for i, p in probs.items() if p[c] >= pii.THRESHOLD}
        truth = {n["id"] for n in rest if n[c]}
        rows.append(
            {
                "category": c,
                "labelled": len(truth),
                "caught": len(flagged & truth),
                "extra flags": len(flagged - truth),
                "recall": len(flagged & truth) / len(truth) if truth else None,
            }
        )
    st.caption(
        "Recall is the metric that matters; precision is what the low threshold costs."
    )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        column_config={"recall": st.column_config.NumberColumn(format="percent")},
    )
with extra:
    st.caption(
        "Some are arguably right (an unnamed meneer is still a private individual); they show the cost of leaning towards recall."
    )
    by_id = {n["id"]: n for n in rest}
    st.dataframe(
        pd.DataFrame(
            [
                {"id": i, "category": c, "p": p[c], "text": by_id[i]["text"]}
                for i, p in probs.items()
                for c in pii.CATEGORIES
                if p[c] >= pii.THRESHOLD and not by_id[i][c]
            ],
            columns=["id", "category", "p", "text"],
        ),
        hide_index=True,
        column_config={"p": ui.P_COLUMN},
    )
with regex:
    st.caption(
        "BSN must pass the 11-check and IBAN mod-97, so an order number doesn't count. A hit skips Jev."
    )
    st.dataframe(
        routed[routed["regex"] != ""][["id", "text", "regex"]], hide_index=True
    )

ui.request_view(*pii.screen_request(notes[0]["text"]))

st.subheader("Your turn")
with st.form("live"):
    text = st.text_area("A Dutch note", pii.LIVE_PRESET, height=80)
    asked = st.form_submit_button("Ask Jev", type="primary")
if asked:
    found = pii.regex_hits(text)
    if found:
        st.metric("Route (Jev not asked)", pii.route(found, {}))
        st.caption(f"regex: {', '.join(sorted(found))}")
    else:
        try:
            answer = ui.judge(ui.mode()).ask(*pii.screen_request(text))
            p = {c: answer.response.nouls[c].noul for c in pii.CATEGORIES}
            st.metric("Route", pii.route(set(), p))
            st.dataframe(
                pd.DataFrame([p]),
                hide_index=True,
                column_config={c: ui.P_COLUMN for c in p},
            )
            st.caption(ui.answer_caption(answer))
        except (NotRecorded, LiveUnavailable) as e:
            st.warning(str(e))

st.subheader("The gate before client data")
st.markdown(
    "This runs on synthetic notes only. Sending client text to an external API to find PII needs the "
    "data-residency question settled first: retention, hosting region and the processing agreement.\n\n"
    "- A regex hit skips Jev, so a note with a phone number and health details is only masked.\n"
    "- Jev says whether a note contains PII, not where. Masking the span is a later step.\n\n"
    "More depth: the jevex demo (`../jevex`) compares regex and Jev on customer-service email."
)
