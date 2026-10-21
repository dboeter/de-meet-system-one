"""Paths, case loading and the append-only raw answer store."""

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"
RAW_DIR = ROOT / "results" / "raw"
OVERRIDES = ROOT / "gold" / "overrides.jsonl"
# Cases mined from the developer's own transcripts. Gitignored: they carry real commands,
# paths and prompts.
PRIVATE = ROOT / "private"

# Case set -> (cases dir, raw answers dir).
CASE_SETS = {
    "synthetic": (CASES_DIR, RAW_DIR),
    "real": (PRIVATE / "cases", PRIVATE / "raw"),
}

Case = dict[str, Any]
Record = dict[str, Any]

# Fields a judge may see. `intended`, `variant`, `group` and `category` stay hidden.
VISIBLE_FIELDS = ("context", "tool_call")


def load_env() -> None:
    """Load KEY=VALUE lines from the repo's .env without overriding the real environment."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(
            key.removeprefix("export ").strip(), value.strip().strip("'\"")
        )


def read_jsonl(path: Path) -> Iterator[Record]:
    with path.open() as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{n}: {e}") from e


def load_cases(case_set: str = "synthetic") -> list[Case]:
    cases_dir = CASE_SETS[case_set][0]
    cases = [c for p in sorted(cases_dir.glob("*.jsonl")) for c in read_jsonl(p)]
    return sorted(cases, key=lambda c: c["id"])


def case_hash(case: Case) -> str:
    """Hash of what the judges see, so an edited case is re-judged instead of reused."""
    visible = {k: case[k] for k in VISIBLE_FIELDS}
    blob = json.dumps(visible, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def judge_state(case: Case, uid: str) -> dict[str, Any]:
    """The judge input. `uid` is a throwaway value so every repeat is an independent draw."""
    return {"uid": uid, **{k: case[k] for k in VISIBLE_FIELDS}}


class RawStore:
    """Append-only JSONL of every call a judge made, successful or not."""

    def __init__(self, judge: str, case_set: str = "synthetic") -> None:
        self.path = CASE_SETS[case_set][1] / f"{judge}.jsonl"

    def records(self) -> list[Record]:
        return list(read_jsonl(self.path)) if self.path.exists() else []

    def done_keys(self) -> set[tuple[str, str, str, int]]:
        return {
            (r["case_id"], r["case_hash"], r["rubric_version"], r["repeat"])
            for r in self.records()
            if r["ok"]
        }

    def append(self, record: Record) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
