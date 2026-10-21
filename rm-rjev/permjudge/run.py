"""Run a judge over the cases and append every answer to results/raw/<judge>.jsonl.

Resumable: a (case, case hash, rubric version, repeat) that already has a successful
record is skipped, so rerunning after a failure or a case edit only does the missing work.
"""

import argparse
import asyncio
import secrets
import time
from typing import Any

from typesafe_sdk import AsyncTypeSafeClient

from permjudge import rubric
from permjudge.common import (
    CASE_SETS,
    RawStore,
    case_hash,
    judge_state,
    load_cases,
    load_env,
)
from permjudge.judges import (
    GO_MODELS,
    OPUS_SCHEMA,
    Judge,
    make_claude,
    make_go,
    make_jev,
)

DEFAULT_CONCURRENCY = {"jev": 8, "opus": 4, "haiku-go": 8, "luna": 8}


async def run(
    name: str, repeats: int, limit: int | None, concurrency: int, case_set: str
) -> None:
    store = RawStore(name, case_set)
    done = store.done_keys()
    cases = load_cases(case_set)
    cases = cases[:limit] if limit else cases
    todo = [
        (case, h, r)
        for case in cases
        for h in [case_hash(case)]
        for r in range(repeats)
        if (case["id"], h, rubric.RUBRIC_VERSION, r) not in done
    ]
    print(f"{name}: {len(cases)} cases x {repeats} repeats, {len(todo)} calls to make")
    if not todo:
        return

    client: AsyncTypeSafeClient | None = None
    if name == "jev":
        client = AsyncTypeSafeClient()
        judge: Judge = make_jev(client)
    elif name == "opus":
        judge = make_claude("opus", OPUS_SCHEMA, effort="high")
    elif name in GO_MODELS:
        judge = make_go(name)
    else:
        raise SystemExit(f"unknown judge {name}")

    gate = asyncio.Semaphore(concurrency)
    counts = {"ok": 0, "failed": 0}
    started = time.monotonic()

    async def one(case: dict[str, Any], h: str, repeat: int) -> None:
        uid = f"{rubric.RUBRIC_VERSION}:{repeat}:{secrets.token_hex(4)}"
        record: dict[str, Any] = {
            "case_id": case["id"],
            "case_hash": h,
            "rubric_version": rubric.RUBRIC_VERSION,
            "repeat": repeat,
            "uid": uid,
            "judge": name,
            "ts": time.time(),
        }
        async with gate:
            try:
                record |= {"ok": True, **await judge(judge_state(case, uid))}
                counts["ok"] += 1
            except Exception as e:  # noqa: BLE001 -- failures are recorded and retried on rerun
                record |= {"ok": False, "error": f"{type(e).__name__}: {e}"}
                counts["failed"] += 1
        store.append(record)
        n = counts["ok"] + counts["failed"]
        if n % 25 == 0 or n == len(todo):
            rate = n / (time.monotonic() - started)
            print(
                f"  {n}/{len(todo)}  failed={counts['failed']}  {rate:.1f}/s",
                flush=True,
            )

    try:
        await asyncio.gather(*(one(c, h, r) for c, h, r in todo))
    finally:
        if client is not None:
            await client.aclose()
    print(f"{name}: ok={counts['ok']} failed={counts['failed']} -> {store.path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("judge", choices=sorted(DEFAULT_CONCURRENCY))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, help="only the first N cases (pilot)")
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--set", default="synthetic", choices=sorted(CASE_SETS))
    args = parser.parse_args()
    load_env()
    concurrency = args.concurrency or DEFAULT_CONCURRENCY[args.judge]
    asyncio.run(run(args.judge, args.repeats, args.limit, concurrency, args.set))


if __name__ == "__main__":
    main()
