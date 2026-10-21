"""Station 4: PII / GDPR screening of free text."""

import csv
import re
from pathlib import Path

from typesafe_sdk import Noul

DATA = Path(__file__).resolve().parent.parent / "data" / "pii_notes.csv"

IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?\b")
BSN = re.compile(r"\b\d{9}\b")
PHONE = re.compile(r"(?<![\d+])(?:\+31|0031|0)(?:[\s-]?\d){9}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

CATEGORIES = {
    "person_name": "Does `text` name a private individual (not a company, brand, or an official acting in their role)?",
    "health": "Does `text` reveal anything about a person's health, illness, disability or medical treatment?",
    "financial": "Does `text` reveal a person's financial situation, such as debts, arrears, income or benefits?",
    "address": "Does `text` give a person's home address, or enough detail to find where they live?",
    "special_category": "Does `text` reveal a person's ethnicity, religion, political opinion, union membership, "
    "sexual orientation, or genetic or biometric data?",
}
# Health and special categories are GDPR Art. 9 data: those rows stay out of gold entirely.
EXCLUDED = {"bsn", "health", "special_category"}
# Code knows where these are, so it can mask them; Jev only says *whether*, not *where*.
MASKABLE = {"iban", "phone", "email"}
THRESHOLD = 0.30  # leans towards recall: a missed flag costs more than a review

# Default input of the notebook's live cell; recorded so it also answers offline.
LIVE_PRESET = "Meneer belde namens zijn moeder, die sinds haar val in een rolstoel zit."


def bsn_valid(digits: str) -> bool:
    """The 11-check: 9×d1 + 8×d2 + … + 2×d8 − 1×d9 is divisible by 11."""
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    return (
        len(digits) == 9
        and sum(w * int(d) for w, d in zip(weights, digits, strict=True)) % 11 == 0
    )


def iban_valid(iban: str) -> bool:
    compact = iban.replace(" ", "")
    rearranged = compact[4:] + compact[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


def regex_hits(text: str) -> set[str]:
    hits = set()
    for match in IBAN.finditer(text):
        if iban_valid(match.group()):
            hits.add("iban")
            text = text.replace(
                match.group(), " "
            )  # IBAN digits must not count as a phone or BSN
    if any(bsn_valid(m.group()) for m in BSN.finditer(text)):
        hits.add("bsn")
    if PHONE.search(text):
        hits.add("phone")
    if EMAIL.search(text):
        hits.add("email")
    return hits


def route(hits: set[str], probabilities: dict[str, float]) -> str:
    flagged = hits | {c for c, p in probabilities.items() if p >= THRESHOLD}
    if flagged & EXCLUDED:
        return "excluded"
    if flagged - MASKABLE:
        return "restricted"
    if flagged:
        return "masked"
    return "clear"


def screen_request(text: str):
    return {"text": text}, {c: Noul(instructions=q) for c, q in CATEGORIES.items()}


def load_notes(path: Path = DATA) -> list[dict]:
    with path.open(newline="") as f:
        return [
            {k: (v == "true" if k in CATEGORIES else v) for k, v in row.items()}
            for row in csv.DictReader(f)
        ]


def requests():
    """Every Jev request the PII notebook makes: rows without a regex hit, plus the live preset."""
    texts = [n["text"] for n in load_notes() if not regex_hits(n["text"])]
    return [screen_request(t) for t in [*texts, LIVE_PRESET]]
