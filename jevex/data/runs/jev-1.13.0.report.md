# Intent judge report: jev-1.13.0

Source: `data/runs/jev-1.13.0.jsonl`, 245 calls over 49 cases. Gold labels: `data/corpus.jsonl`, rubric `data/rubric.md` (single annotator, not yet reviewed).

## Headline

| Metric | Value |
|---|---|
| Accuracy, all calls | 95.9% (235/245) |
| Accuracy, excluding `ambiguous` cases | 95.7% (225/235) |
| Accuracy, easy (regex right) / hard (regex wrong) | 100.0% (95/95) / 93.3% (140/150) |
| Majority-vote accuracy per case | 95.9% (47/49) |
| Regex ladder on the same cases | 38.8% (19/49) |
| Cases with the same label on every repeat | 100.0% (49/49) |
| Gold-label probability spread across repeats, mean / max | 0.016 / 0.320 |
| Latency warm p50 / p95 / max | 215 ms / 255 ms / 368 ms |
| Latency cold (first call) | 295 ms, 278 ms |
| Mean input tokens per call | 443.8 |
| Cost per call (mean) / whole run | $0.0000186 / $0.004567 |
| Cost per 1,000 emails | $0.0186 |
| Failed calls (no retries) | 0 of 245 |

Latency is client wall clock for one HTTPS round trip from this machine, calls in series.

## Accuracy per repeat

| Repeat | Accuracy |
|---|---|
| 0 | 95.9% (47/49) |
| 1 | 95.9% (47/49) |
| 2 | 95.9% (47/49) |
| 3 | 95.9% (47/49) |
| 4 | 95.9% (47/49) |

## Accuracy per gold label

| Gold | Accuracy |
|---|---|
| praise | 100.0% (30/30) |
| refund | 100.0% (50/50) |
| exchange | 80.0% (20/25) |
| complaint | 100.0% (35/35) |
| question | 90.9% (50/55) |
| cancel | 100.0% (30/30) |
| other | 100.0% (20/20) |

## Accuracy by reported confidence

| Confidence | Accuracy |
|---|---|
| 0 – 0.5 | 100.0% (2/2) |
| 0.5 – 0.8 | 70.6% (12/17) |
| 0.8 – 0.95 | 86.1% (31/36) |
| ≥ 0.95 | 100.0% (190/190) |

## Cases answered wrong at least once

| Case | Gold | Labels per repeat | Mean p(gold) | Tags |
|---|---|---|---|---|
| preset-policy | question | refund, refund, refund, refund, refund | 0.07 | preset, hard, policy-question |
| exchange-repair | exchange | other, other, other, other, other | 0.18 | hard, polite-request |

## Cases whose label changed between repeats

None.

## Cases whose p(gold) moved by 0.1 or more between repeats

- preset-negation: spread 0.32, mean p(gold) 0.75, labels exchange, exchange, exchange, exchange, exchange
- cancel-and-refund: spread 0.13, mean p(gold) 0.60, labels cancel, cancel, cancel, cancel, cancel
