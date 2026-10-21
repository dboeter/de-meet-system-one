"""Turn Jev probabilities into pipeline decisions."""

from collections import Counter
from collections.abc import Iterable

BUCKETS = ("accept", "review", "reject")
LO, HI = 0.10, 0.90


def bucket(p: float, lo: float = LO, hi: float = HI) -> str:
    if lo > hi:
        raise ValueError(f"lo ({lo}) must not exceed hi ({hi})")
    if p >= hi:
        return "accept"
    if p <= lo:
        return "reject"
    return "review"


def bucket_counts(
    ps: Iterable[float], lo: float = LO, hi: float = HI
) -> dict[str, int]:
    counts = Counter(bucket(p, lo, hi) for p in ps)
    return {name: counts[name] for name in BUCKETS}
