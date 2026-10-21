"""Call Jev live for every station request that lacks a recording, and append it."""

from jevdemo.judge import Judge
from jevdemo.stations import STATIONS


def main() -> None:
    judge = Judge(mode="live", record=True)
    for name, requests in STATIONS.items():
        todo = [(s, q) for s, q in requests() if not judge.has(s, q)]
        for (state, _), answer in zip(todo, judge.ask_many(todo), strict=True):
            print(f"{name}: {answer.latency_ms:>5} ms  {state}")
        print(f"{name}: recorded {len(todo)}")


if __name__ == "__main__":
    main()
