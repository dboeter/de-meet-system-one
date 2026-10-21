# Intent judge benchmark

Scores a judge (Jev now, Haiku later) on the Intent cases in `data/corpus.jsonl`, labelled
by `data/rubric.md`, for correctness, consistency, latency and cost.

```sh
node scripts/judge/run-jev.ts [--repeats 5] [--dry-run]   # appends to data/runs/<model>.jsonl
node scripts/judge/report.ts [data/runs/<file>.jsonl ...]  # writes data/runs/<file>.report.md
```

The runner only fills missing (case, repeat) pairs, so re-running after a failure is cheap.
It writes nothing to `src/recordings/`.

## Adding a judge

Write a runner that produces `RunLine`s (`runs.ts`) into `data/runs/<judge>.jsonl`, then run
the report. To keep the comparison fair:

- Ask the same question: use `request.questions.intent.instructions` and its `criteria`
  verbatim from the Jev run file, with the email text as the only input.
- One call at a time, retries off, from the same machine, five repeats as whole passes.
- `confidence` and `probabilities` are `null` if the judge returns only a label.
- `cost_usd` uses that judge's own pricing, input and output tokens.
- A call that fails or returns a label outside the seven options is an `error` line.
