"""Live measurements for docs/spec.md: Choice option cap, latency, throughput, cost.

Calls the API; nothing is recorded. Run: uv run python scripts/measure.py
"""

import statistics
import time
from datetime import UTC, datetime

from typesafe_sdk import (
    Choice,
    TypeSafeBadRequestError,
    TypeSafeUnprocessableEntityError,
)

from jevdemo import dq
from jevdemo.judge import MODEL, Judge

PRICE_PER_MTOK = (
    0.042  # USD per million input tokens, output free (docs.typesafe.ai/models)
)
ROWS = 100


def accepts_options(judge: Judge, n: int) -> tuple[bool, str]:
    options = {f"option {i}": None for i in range(n)}
    question = {
        "pick": Choice(instructions="Which option is `value`?", criteria=options)
    }
    try:
        judge.ask({"value": "option 7"}, question)
        return True, ""
    except (TypeSafeBadRequestError, TypeSafeUnprocessableEntityError) as e:
        return False, str(e)[:300]


def synthetic_values(n: int) -> list[str]:
    streets = ["Damrak", "Coolsingel", "Kerkstraat", "Hoofdweg", "Molenweg"]
    junk = ["zie mail", "onbekend", "06-{:08d}", "info{}@example.nl"]
    values = []
    for i in range(n):
        if i % 3:
            values.append(f"{streets[i % 5]} {i + 1}, {1000 + i} AB Amsterdam")
        else:
            values.append(junk[i % 4].format(i))
    return values


def main() -> None:
    judge = Judge(mode="live")

    print("## Choice option cap")
    for n in (255, 256):
        ok, error = accepts_options(judge, n)
        print(f"- {n} options: {'accepted' if ok else 'rejected: ' + error}")

    address = dq.address_check(dq.load_checks())
    requests = [dq.check_request(address, v) for v in synthetic_values(ROWS)]
    print(f"\n## Latency and throughput ({ROWS} distinct values, {MODEL})")
    answers = []
    for concurrency in (1, 8, 16):
        start = time.perf_counter()
        answers = judge.ask_many(requests, concurrency=concurrency)
        wall = time.perf_counter() - start
        latencies = sorted(a.latency_ms for a in answers)
        p95 = latencies[int(0.95 * len(latencies)) - 1]
        print(
            f"- concurrency {concurrency:>2}: {ROWS / wall:5.1f} rows/s, wall {wall:5.1f} s, "
            f"p50 {statistics.median(latencies):.0f} ms, p95 {p95} ms"
        )

    tokens = [a.response.usage.input_tokens or 0 for a in answers]
    per_question = statistics.mean(tokens) * PRICE_PER_MTOK / 1e6
    print("\n## Cost")
    print(f"- mean input tokens per question: {statistics.mean(tokens):.0f}")
    print(
        f"- per question: ${per_question:.8f}; per 1M questions: ${per_question * 1e6:.2f}"
    )
    print(f"\nmeasured {datetime.now(UTC).date().isoformat()}")


if __name__ == "__main__":
    main()
