# jevex: regex vs Jev

A demo that puts a regex a team would really write next to a [Jev](https://docs.typesafe.ai/introduction.md)
judgment on the same customer service email, and shows where the pattern breaks and the
meaning holds. Inspired by [ex-regex](https://github.com/nothans/ex-regex). The spec is in
[docs/spec.md](docs/spec.md).

Six screens, each with the email, the regex column and the Jev column side by side:

| Screen | Jev question | What it shows |
|---|---|---|
| Intent | one Choice | Keyword ladder vs one intent with a probability per option |
| Flags | five Nouls | Several things true at once, each with a review band |
| Triage | Choice + Score + branch Choices | Auto-route, copy a second team, or manual triage by confidence |
| Keep your regex | Choice over regex matches | Regex finds candidates, Jev picks one; the value is copied, never written |
| Scan | one Noul per sentence | Which sentences in a long email need action |
| Scoreboard | (recorded) | Regex vs Jev over the labelled corpus, disagreements, paste your own regex |

Plus a "When to keep the regex" card and a guided presenter mode.

## Run it

Node 22.18 or newer.

```bash
npm install
npm run dev            # http://localhost:5173, API mounted on the same server
```

With no API key every example replays a recorded answer, so the demo runs offline and gives
the same result every time. To ask Jev about new text, put `TYPESAFE_API_KEY` in `.env` (or
the environment) and switch the pill at the top right to **Live**. The key stays on the
server; the browser never sees it.

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with the live API |
| `npm run build` | Recorded-only static site in `dist/`; serve it from any static host, no server needed |
| `npm start` | Production server: serves `dist/` and the live API on `PORT` (default 8787) |
| `npm run record` | Calls Jev for every preset and corpus case that has no recording yet (`-- --dry-run` to count) |
| `npm run eval` | Scores regex vs recorded Jev answers over `data/corpus.jsonl`; writes `eval/results.json` |
| `npm test` | Unit tests, including a check that every preset and corpus case has a recording |
| `npm run e2e` | Playwright: the guided script with the network blocked |
| `npm run typecheck` | `tsc` |

Live mode limits, set in the environment: `JEVEX_MAX_REQUESTS` (live requests per server
process, default 500) and `JEVEX_MAX_DAILY_TOKENS` (input tokens per UTC day, default
2,000,000). Input text is capped at 4,000 characters. Each request reserves an upper-bound
token estimate before it is sent, so the daily cap is not overshot; failed calls still count
toward the request cap. When a cap is reached the mode pill says so and Ask shows the cap
error without calling the server.

## Presenting

Open `#/guided/1` or press **Guided**. `→`/`←` step through the script, `N` shows speaker
notes (**Open on another screen** pops them into a window that follows the steps), `L` opens
an empty email (the guided "your turn" step, or the current screen blank in free play) and
switches to Live if the server has a key, `+`/`−` zoom. The script is in `src/web/guided.ts`.

## Measured results

Model `jev-1.13.0`, intent recorded 2026-10-20, flags and triage 2026-10-21.

**Labelled corpus** (`npm run eval`: 49 intent, 39 flags and 35 triage emails; cases tagged
ambiguous are excluded, 2 per station). Flags count 5 decisions per email.

| Task | Decisions | Regex | Jev | Gap vs repeat noise |
|---|---|---|---|---|
| Intent | 47 | 40% (19) | 96% (45) | +26; noise could move at most 14 |
| Flags | 190 | 84% (159) | 95% (180), 10 to review, 0 wrong | +21; noise could move at most 18 |
| Triage: team | 33 | 58% (19) | 97% (32) | +13; noise could move at most 4 |
| Triage: urgency | 33 | 76% (25) | 94% (31) | +6; noise could move at most 5 |

The corpus and its labelling rubric (`data/rubric.md`) were written before the answers were
scored. Repeat noise is measured per task, on that task's own decision only (an unused
branch question changing does not count). Every flags and triage case was asked 3 times,
intent's first 10. Flags: 0 of 39 cases changed (largest probability move 0.08). Triage
team: 0 of 35. Triage urgency: 1 of 35, `triage-took-twice`, whose urgency score sat at
1.49–1.54 around the 1.5 cut-off. Intent: 0 of 10 (largest move 0.04). "At most N" is the
95% upper bound of the flip rate applied to the task's decisions; a flags case that flips
may flip all 5. Every gap is beyond that bound; triage urgency only just (+6 vs 5).
Flags are scored with the same
yes / review / no bands the Flags screen uses; a flag in the review band counts as
"to review", neither right nor wrong. The session
that wrote the corpus also ran all 49 intent cases 5× (those run files are not in this repo):
the same two cases were wrong every time, and one preset's confidence moved from 0.85 to 0.48
without its answer changing. Treat single-run confidences as approximate.

**Presets** (the examples on each screen):

| Screen | Regex right | Jev right |
|---|---|---|
| Intent | 0 of 7 | 6 of 7 |
| Triage (team) | 1 of 4 | 4 of 4 |
| Keep your regex | 0 of 3 (first match) | 3 of 3 |
| Scan (sentences) | 4 of 9 | 9 of 9 |

Presets were written to show where the regex breaks, so the preset table is not an accuracy
estimate; the corpus is.

Where Jev is wrong or unsure, the demo shows it:

- Intent, "Can I get my money back if it's still sealed?": Jev answers `refund` (0.94); the
  label is `question`. Shown with a ✗ in free play; not in the guided script.
- Intent corpus, "Can you repair it under warranty?": Jev answers `other`; the label is
  `exchange`. The `exchange` option's description does not mention repair. The wording was
  frozen before the corpus was scored and has not been tuned on it.
- Flags, "Third time writing…": `wants_human` is 0.74, in the review band with the default
  thresholds. "Not a lawyer": `cancellation_risk` 0.23, also review.

## Limits

- Use a regex for shape and code for counting: format validation, exact IDs, totals and dates
  are not questions about meaning.
- Thresholds shown are illustrative, tuned on nothing. Measure on your own labelled data and
  pin the model before relying on one.
- Jev picks only among candidates the regex found; a value the finder misses cannot be picked.
- Recorded answers belong to one model. Changing the model or any question's wording changes
  the recording key; run `npm run record` again.

## Layout

```
src/core/          station modules (regex baselines, questions, interpretation), recordings, eval
src/server/        /api/ask and /api/health, SDK client, production server
src/web/           React UI, guided script
src/recordings/    recordings.jsonl, one recorded Jev call per line
data/              corpus.jsonl (labelled cases), rubric.md
scripts/           record.ts, eval.ts
e2e/               Playwright smoke test
```
