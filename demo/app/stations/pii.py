import pandas as pd
import results
import streamlit as st

import ui
from jevdemo import pii
from jevdemo.judge import LiveUnavailable, NotRecorded

finding = ui.header("PII screening of free text", "04_pii.ipynb")

CATEGORY_NAMES = {
    "person_name": "Names a person",
    "health": "Health",
    "financial": "Finances",
    "address": "Home address",
    "special_category": "Other sensitive (Art. 9)",
}

notes, hits, rest = results.NOTES, results.HITS, results.UNSETTLED
probs = results.pii_probs(ui.mode())
routed = results.pii_routed(probs)
routes = routed["route"].value_counts()
ui.claim(finding, results.pii_claim(routed))

if ui.presenting():
    chart = st.container()
else:
    left, chart = st.columns([1, 2], gap="large")
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
with chart:
    long = pd.DataFrame(
        [
            {
                "id": i,
                "category": CATEGORY_NAMES.get(c, c),
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
        x_title="Jev's confidence that the note contains it",
    )
    st.caption(
        f"One dot per note and kind of data, for the {len(rest)} notes regex found nothing in. "
        f"Right of {pii.THRESHOLD:.2f} the note is flagged: low on purpose, because a missed flag "
        "costs more than a review."
    )

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
    "data-residency question settled first: retention, hosting region and the processing agreement."
)

ui.end_of_presenter_view()

st.markdown(
    "- A regex hit skips Jev, so a note with a phone number and health details is only masked.\n"
    "- Jev says whether a note contains PII, not where. Masking the span is a later step.\n\n"
    "More depth: the jevex demo (`../jevex`) compares regex and Jev on customer-service email."
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
