"""Station 3: map a legacy source schema onto a target model."""

import csv
import re
from collections import Counter
from pathlib import Path

import yaml
from typesafe_sdk import Choice

DATA = Path(__file__).resolve().parent.parent / "data"

# Declared by the consultant: which target tables a source table can feed.
TABLES = {"KLANT": ["customer"], "ORDER": ["order", "invoice"]}
MAX_OPTIONS = 255  # measured Choice cap (spec.md, Measured during the build)
CONFIDENT = 0.80
NONE = "none"

SOURCE_FAMILY = {"NUMBER": "number", "DATE": "date"}  # anything else is text
TARGET_FAMILY = {
    "integer": "number",
    "decimal": "number",
    "date": "date",
    "timestamp": "date",
}

QUESTION = "Which target column holds the same data as `source_column`?"

# Default input of the notebook's live cell; recorded so it also answers offline.
LIVE_PRESET = {
    "source_col": "KLANT.KLT_IBAN",
    "type": "VARCHAR2(34)",
    "comment": "",
    "samples": ["NL91ABNA0417164300", "NL20INGB0001234567", ""],
}


def load_csv(name: str) -> list[dict]:
    with (DATA / f"schema_{name}.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def load_sources() -> list[dict]:
    return [{**row, "samples": row["samples"].split("|")} for row in load_csv("source")]


def load_targets() -> list[dict]:
    return load_csv("target")


def load_gold() -> dict[str, str]:
    return {row["source_col"]: row["target_col"] for row in load_csv("gold")}


def compatible(source_type: str, target_type: str) -> bool:
    family = SOURCE_FAMILY.get(re.sub(r"\(.*", "", source_type), "text")
    # Legacy text columns hold anything: dates as CHAR(8), flags as CHAR(1).
    return family == "text" or family == TARGET_FAMILY.get(target_type, "text")


def shortlist(source: dict, targets: list[dict]) -> list[str]:
    tables = TABLES[source["source_col"].split(".")[0]]
    options = [
        t["target_col"]
        for t in targets
        if t["target_col"].split(".")[0] in tables
        and compatible(source["type"], t["type"])
    ]
    if len(options) + 1 > MAX_OPTIONS:
        raise ValueError(
            f"{len(options) + 1} options exceed the Choice cap of {MAX_OPTIONS}"
        )
    return [*options, NONE]


def mapping_request(source: dict, targets: list[dict]):
    described = {t["target_col"]: f"{t['description']} ({t['type']})" for t in targets}
    criteria = {
        o: described.get(o, "No target column holds this data")
        for o in shortlist(source, targets)
    }
    state = {
        "source_column": {
            "name": source["source_col"],
            "type": source["type"],
            "comment": source["comment"] or None,
            "samples": [s for s in source["samples"] if s],
        }
    }
    return state, {"target": Choice(instructions=QUESTION, criteria=criteria)}


def to_mapping(source: dict, response) -> dict:
    choice = response.choices["target"]
    return {
        "source_col": source["source_col"],
        "target_col": choice.choice,
        "p": choice.probabilities[choice.choice],
    }


def decide(mappings: list[dict]) -> list[dict]:
    claimed = Counter(m["target_col"] for m in mappings if m["target_col"] != NONE)
    decided = []
    for m in mappings:
        if m["target_col"] != NONE and claimed[m["target_col"]] > 1:
            reason = "1:1 conflict"
        elif m["p"] < CONFIDENT:
            reason = "low confidence"
        else:
            reason = ""
        decided.append(
            {**m, "decision": "review" if reason else "accept", "reason": reason}
        )
    return decided


def evaluate(rows: list[dict], gold: dict[str, str]) -> dict:
    n = len(rows)
    nones = [r for r in rows if gold[r["source_col"]] == NONE]
    correct = [r for r in rows if r["target_col"] == gold[r["source_col"]]]
    return {
        "top1_accuracy": len(correct) / n,
        "shortlist_recall": sum(gold[r["source_col"]] in r["shortlist"] for r in rows)
        / n,
        "none_accuracy": sum(r["target_col"] == NONE for r in nones) / len(nones)
        if nones
        else 1.0,
        "prefilled_correct": sum(r["decision"] == "accept" for r in correct) / n,
    }


def sources_yml(rows: list[dict], source_name: str) -> str:
    tables: dict[str, list[dict]] = {}
    for r in rows:
        if r["decision"] != "accept":
            continue
        table, column = r["source_col"].split(".")
        tables.setdefault(table, []).append(
            {
                "name": column,
                "description": "no target equivalent"
                if r["target_col"] == NONE
                else f"maps to {r['target_col']}",
                "meta": {"target": r["target_col"], "p": round(r["p"], 2)},
            }
        )
    doc = {
        "version": 2,
        "sources": [
            {
                "name": source_name,
                "tables": [{"name": t, "columns": c} for t, c in tables.items()],
            }
        ],
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def requests():
    """Every Jev request the schema-mapping notebook makes."""
    targets = load_targets()
    return [mapping_request(s, targets) for s in [*load_sources(), LIVE_PRESET]]
