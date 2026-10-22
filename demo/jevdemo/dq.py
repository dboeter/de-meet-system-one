"""Station 1: semantic data-quality checks on silver-layer columns."""

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from typesafe_sdk import Choice, Noul

from jevdemo.pipeline import HI, LO, bucket

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "dq_rows.csv"
CHECKS = ROOT / "checks.yaml"
CHECK_VARIANTS = ROOT / "checks_variants.yaml"

# Default input of the notebook's live cell; recorded so it also answers offline.
LIVE_PRESET = "Achter de kerk, het witte huis"


@dataclass(frozen=True)
class Check:
    id: str
    column: str
    kind: Literal["noul", "choice"]
    check: str
    max_fail_rate: float
    action: Literal["warn", "quarantine", "fail_run"]
    codes: dict[str, str] | None = None
    # Choice only: set → split into a pass Noul plus a code Choice.
    question: str | None = None


@dataclass(frozen=True)
class Judgment:
    check_id: str
    value: str
    p_pass: float
    code: str | None = None


@dataclass
class CacheStats:
    asked: int
    cached: int

    @property
    def hit_rate(self) -> float:
        total = self.asked + self.cached
        return self.cached / total if total else 0.0


@dataclass
class Cache:
    """Answers keyed by (check_id, value_hash), shared across pipeline runs."""

    entries: dict[tuple[str, str], Judgment] = field(default_factory=dict)

    @staticmethod
    def key(check: Check, value: str) -> tuple[str, str]:
        return check.id, hashlib.sha256(value.encode()).hexdigest()


def load_rows(path: Path = DATA) -> list[dict]:
    with path.open(newline="") as f:
        return [
            {
                **row,
                "is_address": row["is_address"] == "true",
                "is_product_description": row["is_product_description"] == "true",
            }
            for row in csv.DictReader(f)
        ]


def load_checks(path: Path = CHECKS) -> list[Check]:
    checks = [Check(**c) for c in yaml.safe_load(path.read_text())["checks"]]
    for c in checks:
        if c.kind == "choice" and "other" not in (c.codes or {}):
            raise ValueError(
                f"choice check {c.id} needs an `other` code: picking it is how a value fails"
            )
    return checks


def address_check(checks: list[Check]) -> Check:
    return next(c for c in checks if c.column == "address")


def distinct_values(rows: list[dict], column: str) -> list[str]:
    # Distinct values are far fewer than rows; ask Jev once per value.
    return list(dict.fromkeys(row[column] for row in rows))


def check_request(check: Check, value: str):
    state = {"column": check.column, "value": value}
    passes = Noul(
        instructions=f"Does `value` from column `{check.column}` pass this check: it {check.check}?"
    )
    if check.kind == "noul":
        return state, {"passes": passes}
    if check.question is None:
        return state, {
            "code": Choice(instructions=check.check, criteria=check.codes or {})
        }
    codes = check.codes or {}
    state["codes"] = {code: d for code, d in codes.items() if code != "other"}
    return state, {
        "passes": passes,
        "code": Choice(instructions=check.question, criteria=codes),
    }


def to_judgment(check: Check, value: str, response) -> Judgment:
    if check.kind == "choice":
        answer = response.choices["code"]
        p_pass = (
            1 - answer.probabilities["other"]
            if check.question is None
            else response.nouls["passes"].noul
        )
        return Judgment(check.id, value, p_pass, answer.choice)
    return Judgment(check.id, value, response.nouls["passes"].noul)


def judge_checks(
    rows, checks, judge, cache: Cache
) -> tuple[list[Judgment], CacheStats]:
    todo = [
        (check, value)
        for check in checks
        for value in distinct_values(rows, check.column)
        if Cache.key(check, value) not in cache.entries
    ]
    answers = judge.ask_many([check_request(c, v) for c, v in todo])
    for (check, value), answer in zip(todo, answers, strict=True):
        cache.entries[Cache.key(check, value)] = to_judgment(
            check, value, answer.response
        )

    judgments = [
        cache.entries[Cache.key(check, value)]
        for check in checks
        for value in distinct_values(rows, check.column)
    ]
    return judgments, CacheStats(asked=len(todo), cached=len(judgments) - len(todo))


def requests():
    """Every request the DQ notebook makes, for recording and the completeness test."""
    rows, checks = load_rows(), load_checks()
    address = address_check(checks)
    return [
        *(
            check_request(c, v)
            for c in [*checks, *load_checks(CHECK_VARIANTS)]
            for v in distinct_values(rows, c.column)
        ),
        check_request(address, LIVE_PRESET),
    ]


@dataclass(frozen=True)
class RunResult:
    rows: list[dict]  # one per (row, check), with p_pass and decision
    quarantine: list[dict]
    manifest: dict


def run(rows, checks, judgments, lo: float = LO, hi: float = HI) -> RunResult:
    """Pure: thresholds turn judgments into decisions; no API calls, so rerunning is free."""
    by_key = {(j.check_id, j.value): j for j in judgments}
    decided, quarantine = [], []
    manifest: dict = {"checks": {}}
    for check in checks:
        counts = {"accept": 0, "review": 0, "reject": 0}
        for row in rows:
            judgment = by_key[(check.id, row[check.column])]
            decision = bucket(judgment.p_pass, lo, hi)
            counts[decision] += 1
            result = {
                "row_id": row["row_id"],
                "check_id": check.id,
                "value": judgment.value,
                "p_pass": judgment.p_pass,
                "code": judgment.code,
                "decision": decision,
            }
            decided.append(result)
            if decision == "reject" and check.action != "warn":
                quarantine.append(result)
        fail_rate = counts["reject"] / len(rows) if rows else 0.0
        manifest["checks"][check.id] = {
            **counts,
            "fail_rate": fail_rate,
            "max_fail_rate": check.max_fail_rate,
            "action": check.action,
            "triggered": fail_rate > check.max_fail_rate,
        }
    fired = [c["action"] for c in manifest["checks"].values() if c["triggered"]]
    manifest["status"] = "failed" if "fail_run" in fired else "warn" if fired else "ok"
    return RunResult(decided, quarantine, manifest)
