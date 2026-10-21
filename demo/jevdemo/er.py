"""Station 2: entity resolution across two supplier tables."""

import csv
import re
import unicodedata
from pathlib import Path

from typesafe_sdk import Noul, NoulCriteria

DATA = Path(__file__).resolve().parent.parent / "data"

ABBREVIATIONS = {r"\bgem\.": "gemeente", r"\bafd\.": "afdeling"}
LEGAL_FORMS = r"\b(b\.?v\.?|n\.?v\.?|u\.?a\.?|v\.?o\.?f\.?|zn\.?)(?=\W|$)"
# Words too common to block on: legal and sector words, articles.
STOPWORDS = {
    "gemeente", "stichting", "koninklijke", "cooperatieve", "de", "het", "van", "der", "den", "t",
    "cafe", "hotel", "bakkerij", "bouwbedrijf", "drukkerij", "brouwerij", "afdeling",
}  # fmt: skip

# Chosen on this same small set (no holdout): every gold pair scored >= 0.74, every other <= 0.40.
LO, HI = 0.30, 0.70

# Default input of the notebook's live cell; recorded so it also answers offline.
LIVE_PRESET = (
    {"id": "A90", "name": "Jansen B.V.", "street": "Industrieweg 12", "postcode": "3044 AS",
     "city": "Rotterdam", "kvk": "24123456", "iban": ""},
    {"id": "B90", "name": "Jansen Holding", "street": "Industrieweg 12", "postcode": "3044 AS",
     "city": "Rotterdam", "kvk": "", "iban": ""},
)  # fmt: skip

SAME_ORGANISATION = Noul(
    instructions="Do `a` and `b` refer to the same real-world organisation?",
    criteria=NoulCriteria(
        true="The same organisation, including a department or branch of it, a trading name, "
        "or the same organisation after a name change.",
        false="Different organisations, including a parent and its separately registered "
        "subsidiary, or unrelated organisations with similar names.",
    ),
)


def load_table(name: str) -> list[dict]:
    with (DATA / f"er_suppliers_{name}.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def load_gold() -> set[tuple[str, str]]:
    with (DATA / "er_gold.csv").open(newline="") as f:
        return {(row["id_a"], row["id_b"]) for row in csv.DictReader(f)}


def normalize_name(name: str) -> str:
    text = (
        unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    )
    for pattern, expansion in ABBREVIATIONS.items():
        text = re.sub(pattern, expansion, text)
    text = re.sub(LEGAL_FORMS, " ", text)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def phonetic_key(name: str) -> str:
    """First four sounds of the first distinctive word: crude, but catches spelling variants."""
    words = [w for w in normalize_name(name).split() if w not in STOPWORDS]
    if not words:
        return ""
    word = words[0]
    for a, b in (
        ("ij", "y"),
        ("ph", "f"),
        ("dt", "t"),
        ("th", "t"),
        ("c", "k"),
        ("z", "s"),
    ):
        word = word.replace(a, b)
    consonants = word[0] + re.sub(r"[aeiouy]", "", word[1:])
    return re.sub(r"(.)\1+", r"\1", consonants)[:4]


def blocking_keys(record: dict) -> set[str]:
    keys = {f"pc:{record['postcode'][:4]}"} if record["postcode"] else set()
    if record["kvk"]:
        keys.add(f"kvk:{record['kvk'][:4]}")
    if phonetic := phonetic_key(record["name"]):
        keys.add(f"ph:{phonetic}")
    return keys


def candidate_pairs(a: list[dict], b: list[dict]) -> list[tuple[dict, dict]]:
    b_keys = [(rb, blocking_keys(rb)) for rb in b]
    return [
        (ra, rb)
        for ra in a
        if (a_keys := blocking_keys(ra))
        for rb, keys in b_keys
        if a_keys & keys
    ]


def exact_match(ra: dict, rb: dict) -> bool:
    return any(ra[field] and ra[field] == rb[field] for field in ("kvk", "iban"))


def pair_request(ra: dict, rb: dict):
    def describe(record):
        return {k: v or None for k, v in record.items() if k != "id"}

    return {"a": describe(ra), "b": describe(rb)}, {"same": SAME_ORGANISATION}


def levenshtein(s: str, t: str) -> int:
    previous = list(range(len(t) + 1))
    for i, cs in enumerate(s, 1):
        current = [i]
        for j, ct in enumerate(t, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (cs != ct))
            )
        previous = current
    return previous[-1]


def name_similarity(ra: dict, rb: dict) -> float:
    """The fuzzy baseline: 1 - edit distance / length, on normalized names."""
    x, y = normalize_name(ra["name"]), normalize_name(rb["name"])
    return 1 - levenshtein(x, y) / max(len(x), len(y), 1)


def clusters(ids: list[str], merges: list[tuple[str, str]]) -> dict[str, str]:
    parent = {i: i for i in ids}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for x, y in merges:
        rx, ry = find(x), find(y)
        parent[max(rx, ry)] = min(rx, ry)
    return {i: find(i) for i in ids}


def evaluate(decisions: dict[tuple[str, str], str], gold: set[tuple[str, str]]) -> dict:
    merged = {pair for pair, d in decisions.items() if d == "accept"}
    return {
        "precision": len(merged & gold) / len(merged) if merged else 1.0,
        "recall": len(merged & gold) / len(gold),
        "review": sum(d == "review" for d in decisions.values()),
        "merged": len(merged),
    }


def requests():
    """Every Jev request the entity-resolution notebook makes."""
    pairs = candidate_pairs(load_table("a"), load_table("b"))
    return [
        *(pair_request(ra, rb) for ra, rb in pairs if not exact_match(ra, rb)),
        pair_request(*LIVE_PRESET),
    ]
