"""Validate the case files: `python -m permjudge.cases check`."""

import sys
from collections import Counter

from permjudge import rubric
from permjudge.common import CASES_DIR, load_cases

FIELDS = {"id", "group", "category", "variant", "intended", "context", "tool_call"}
CATEGORIES = {
    "read_only", "build_test", "file_edits", "destructive_fs", "git_vcs", "secrets",
    "network_egress", "package_install", "privilege_system", "cloud_db", "obfuscation",
    "scope_mismatch", "prompt_injection", "chained",
}  # fmt: skip
TOOL_INPUTS = {
    "Bash": {"command"},
    "Read": {"file_path"},
    "Write": {"file_path", "content"},
    "Edit": {"file_path", "old_string", "new_string"},
    "WebFetch": {"url", "prompt"},
    "Grep": {"pattern"},
    "Glob": {"pattern"},
}


def check() -> list[str]:
    cases = load_cases()
    errors: list[str] = []
    ids = Counter(c.get("id") for c in cases)
    errors += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    by_id = {c["id"]: c for c in cases}
    for c in cases:
        cid = c.get("id")
        if set(c) != FIELDS:
            errors.append(f"{cid}: fields {sorted(set(c) ^ FIELDS)} differ from schema")
            continue
        if c["category"] not in CATEGORIES:
            errors.append(f"{cid}: unknown category {c['category']}")
        if c["intended"] not in rubric.LABELS:
            errors.append(f"{cid}: bad intended {c['intended']}")
        if c["variant"] == "base":
            if c["group"] != cid:
                errors.append(f"{cid}: base case group must equal its id")
        elif c["variant"] in ("paraphrase", "minimal"):
            base = by_id.get(c["group"])
            if base is None or base["variant"] != "base":
                errors.append(f"{cid}: group {c['group']} is not a base case")
            elif c["category"] != base["category"]:
                errors.append(f"{cid}: category differs from its base")
            # A paraphrase keeps its base's label; a minimal edit flips it.
            elif (c["intended"] == base["intended"]) != (c["variant"] == "paraphrase"):
                errors.append(
                    f"{cid}: intended {c['intended']} breaks its {c['variant']} pair"
                )
        else:
            errors.append(f"{cid}: bad variant {c['variant']}")
        ctx, call = c["context"], c["tool_call"]
        if not {"cwd", "user_request"} <= set(ctx):
            errors.append(f"{cid}: context needs cwd and user_request")
        if c["category"] == "prompt_injection" and not ctx.get("recent_tool_output"):
            errors.append(f"{cid}: prompt_injection case without recent_tool_output")
        needed = TOOL_INPUTS.get(call.get("tool_name"))
        if needed is None:
            errors.append(f"{cid}: unknown tool {call.get('tool_name')}")
        elif not needed <= set(call.get("tool_input", {})):
            errors.append(f"{cid}: {call['tool_name']} input missing {needed}")
    return errors


def summary() -> str:
    cases = load_cases()
    lines = [f"{len(cases)} cases in {CASES_DIR}"]
    for cat in sorted({c["category"] for c in cases}):
        cs = [c for c in cases if c["category"] == cat]
        variants = Counter(c["variant"] for c in cs)
        labels = Counter(c["intended"] for c in cs if c["variant"] == "base")
        lines.append(
            f"  {cat:18} base={variants['base']:3} para={variants['paraphrase']:3} "
            f"min={variants['minimal']:3}  base intended: "
            + " ".join(f"{k}={labels[k]}" for k in rubric.LABELS)
        )
    return "\n".join(lines)


if __name__ == "__main__":
    if sys.argv[1:] != ["check"]:
        raise SystemExit("usage: python -m permjudge.cases check")
    problems = check()
    print(summary())
    print("\n".join(problems) or "ok")
    sys.exit(1 if problems else 0)
