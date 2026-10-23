"""Each station's judged results and its result in one sentence, shared by the station pages and the overview."""

import pandas as pd
import streamlit as st

import ui
from jevdemo import dq, er, pii, schema
from jevdemo.pipeline import bucket

# The station table on the guided walkthrough's second step.
STATIONS = pd.DataFrame(
    [
        (
            "Data quality",
            "Asks once per distinct value and remembers the answer",
            "Does this value pass the check? Which cancel code is this?",
        ),
        (
            "Entity resolution",
            "Pairs likely candidates, merges on a matching KvK or IBAN",
            "Are these two suppliers the same organisation?",
        ),
        (
            "Schema mapping",
            "Shortlists target columns by table and type",
            "Which target column holds this source column's data?",
        ),
        (
            "PII screening",
            "Finds BSN, IBAN, phone numbers and email with regex",
            "Does this note name a person, or reveal health, finances, an address or other sensitive data?",
        ),
    ],
    columns=["Station", "What code does first", "What Jev is asked"],
).set_index("Station")

# --- Data quality ---

ROWS, CHECKS = dq.load_rows(), dq.load_checks()
# Checks are config, so an unknown id falls back to itself.
CHECK_NAMES = {
    "address_is_postal": ("Address", "addresses"),
    "description_names_product": ("Product description", "product descriptions"),
    "cancel_reason_code": ("Cancel reason", "cancel reasons"),
}


def check_label(cid: str) -> str:
    return CHECK_NAMES.get(cid, (cid, cid))[0]


@st.cache_data(show_spinner="Asking Jev…")
def dq_judgments(mode: str):
    # Two passes over one cache: the second is tomorrow's run, with nothing new to ask.
    cache = dq.Cache()
    judgments, first = dq.judge_checks(ROWS, CHECKS, ui.judge(mode), cache)
    _, rerun = dq.judge_checks(ROWS, CHECKS, ui.judge(mode), cache)
    return judgments, first, rerun


def dq_claim(result) -> str:
    distinct = pd.DataFrame(result.rows).drop_duplicates(["check_id", "value"])
    review = int((distinct["decision"] == "review").sum())
    return (
        f"Jev decides {len(distinct) - review} of {len(distinct)} distinct values on its own; "
        f"{review} go to review."
    )


# --- Entity resolution ---

# The fuzzy-match baseline cuts name similarity here; Jev's own cuts are er.LO / er.HI.
BASELINE_CUTS = (0.50, 0.85)

ER_A, ER_B, ER_GOLD = er.load_table("a"), er.load_table("b"), er.load_gold()
PAIRS = er.candidate_pairs(ER_A, ER_B)
EXACT = [(ra, rb) for ra, rb in PAIRS if er.exact_match(ra, rb)]
AMBIGUOUS = [(ra, rb) for ra, rb in PAIRS if not er.exact_match(ra, rb)]


@st.cache_data(show_spinner="Asking Jev…")
def er_p_same(mode: str) -> dict[tuple[str, str], float]:
    answers = ui.judge(mode).ask_many([er.pair_request(ra, rb) for ra, rb in AMBIGUOUS])
    return {
        (ra["id"], rb["id"]): ans.response.nouls["same"].noul
        for (ra, rb), ans in zip(AMBIGUOUS, answers, strict=True)
    }


def er_matches(p_same, lo: float, hi: float) -> list[dict]:
    return [
        {
            "id_a": ra["id"],
            "id_b": rb["id"],
            "p_same": 1.0,
            "decision": "accept",
            "by": "exact rule",
        }
        for ra, rb in EXACT
    ] + [
        {"id_a": x, "id_b": y, "p_same": p, "decision": bucket(p, lo, hi), "by": "Jev"}
        for (x, y), p in p_same.items()
    ]


def er_baseline() -> dict[tuple[str, str], str]:
    """Levenshtein on normalized names, with the same exact rule in front."""
    return {
        (ra["id"], rb["id"]): "accept"
        if er.exact_match(ra, rb)
        else bucket(er.name_similarity(ra, rb), *BASELINE_CUTS)
        for ra, rb in PAIRS
    }


def er_claim(scores: dict) -> str:
    def found(s):
        right = round(s["recall"] * len(ER_GOLD))
        return right, s["merged"] - right

    (jr, jw), (fr, _) = found(scores["Jev"]), found(scores["Levenshtein"])
    wrong = "no wrong merge" if not jw else f"{jw} wrong merge{'s' * (jw > 1)}"
    return (
        f"Jev finds {jr} of {len(ER_GOLD)} duplicate suppliers, with {wrong}. "
        f"Name matching finds {fr}."
    )


# --- Schema mapping ---

SOURCES, TARGETS, SCHEMA_GOLD = (
    schema.load_sources(),
    schema.load_targets(),
    schema.load_gold(),
)
SHORTLISTS = {s["source_col"]: schema.shortlist(s, TARGETS) for s in SOURCES}


@st.cache_data(show_spinner="Asking Jev…")
def schema_mappings(mode: str) -> list[dict]:
    answers = ui.judge(mode).ask_many(
        [schema.mapping_request(s, TARGETS) for s in SOURCES]
    )
    return schema.decide(
        [
            {
                **schema.to_mapping(s, a.response),
                "shortlist": SHORTLISTS[s["source_col"]],
            }
            for s, a in zip(SOURCES, answers, strict=True)
        ]
    )


def schema_table(decided: list[dict]) -> pd.DataFrame:
    table = pd.DataFrame(decided)[
        ["source_col", "target_col", "p", "decision", "reason"]
    ]
    table["gold"] = table["source_col"].map(SCHEMA_GOLD)
    table["correct"] = table["target_col"] == table["gold"]
    return table


def schema_claim(table: pd.DataFrame) -> str:
    prefilled = table["decision"] == "accept"
    right, wrong = (
        int((prefilled & table["correct"]).sum()),
        int((prefilled & ~table["correct"]).sum()),
    )
    return f"Jev pre-fills {right + wrong} of {len(table)} column mappings, " + (
        "none of them wrong." if not wrong else f"{wrong} of them wrong."
    )


# --- PII screening ---

CATEGORY_NAMES = {
    "person_name": "Names a person",
    "health": "Health",
    "financial": "Finances",
    "address": "Home address",
    "special_category": "Other sensitive",
}
GATE = "This runs on synthetic notes only."

NOTES = pii.load_notes()
HITS = {n["id"]: pii.regex_hits(n["text"]) for n in NOTES}
UNSETTLED = [
    n for n in NOTES if not HITS[n["id"]]
]  # regex found nothing: Jev screens these


@st.cache_data(show_spinner="Asking Jev…")
def pii_probs(mode: str) -> dict[str, dict[str, float]]:
    answers = ui.judge(mode).ask_many(
        [pii.screen_request(n["text"]) for n in UNSETTLED]
    )
    return {
        n["id"]: {c: a.response.nouls[c].noul for c in pii.CATEGORIES}
        for n, a in zip(UNSETTLED, answers, strict=True)
    }


def pii_routed(probs) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": n["id"],
                "text": n["text"],
                "regex": ", ".join(sorted(HITS[n["id"]])),
                "route": pii.route(HITS[n["id"]], probs.get(n["id"], {})),
            }
            for n in NOTES
        ]
    )


def pii_claim(routed: pd.DataFrame) -> str:
    contextual = [n for n in NOTES if any(n[c] for c in pii.CATEGORIES)]
    route = routed.set_index("id")["route"]
    by_regex = sum(bool(HITS[n["id"]]) for n in contextual)
    by_jev = sum(route[n["id"]] != "clear" for n in contextual)
    numbered = sum(bool(h) for h in HITS.values())
    return (
        f"Regex finds {by_regex} of the {len(contextual)} notes whose personal details are in "
        f"context (health, finances, address…). It catches the {numbered} with a BSN, IBAN, "
        f"phone or email. With Jev: {by_jev}."
    )


# Written, not computed: notebooks/05_lessons.ipynb recomputes the runs behind it.
LESSONS_CLAIM = (
    "Clearer wording helped; splitting the cancel-reason question in two didn't."
)
