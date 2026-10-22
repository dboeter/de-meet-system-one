# jevex: regex vs Jev demo — spec

A web demo that puts a regex a team would really write next to a Jev judgment on the
same text, and shows where the pattern breaks and the meaning holds. The lead use case is
customer service email: refund requests, complaints, routing, picking the right order
number. Inspired by [ex-regex](https://github.com/nothans/ex-regex) and its
[playground](https://nothans.github.io/ex-regex/).

## Decisions

| Topic | Decision |
|---|---|
| Stack | TypeScript. Vite + React front end, a small Node server that holds `TYPESAFE_API_KEY` and calls `@typesafe-ai/sdk` (0.7.0, Node 22+). The key never reaches the browser. |
| Answers | Recorded by default: every preset replays a recorded Jev response, so the demo runs offline, free and the same every time. A live toggle sends audience-typed text to Jev through the server. |
| Audience | Both: a guided presenter path through the stations, and free play on the same screens. |
| Model | Pinned versioned ID in one config value, default `jev-1.13.0` (what `jev-latest` points to today). Recordings store the `model` field the response returned. |

## Goals

1. In under five minutes, a presenter shows four or five cases where a reasonable regex
   gives the wrong answer and Jev gives the right one, each with a probability.
2. Show what a regex cannot express: probability, a threshold the viewer controls, and an
   "unsure, send to a person" band.
3. Show that Jev and regex combine: a regex proposes candidates, Jev picks one. Jev picks
   only from the given spans, so it can be wrong but never invents a value.
4. Let anyone in the room type their own email and see both sides answer it live.
5. Back the claims with a small labelled corpus and a scoreboard (regex accuracy vs Jev
   accuracy), not only hand-picked presets.

## Non-goals

- A library or a clone of Python's `re` API. ex-regex already covers that; jevex is a
  use-case demo.
- Shape and counting tasks (valid IPv4, balanced brackets, date arithmetic). The demo says
  so on the "When to keep the regex" card instead of hiding it.
- Production thresholds. Thresholds shown are illustrative.
- Auth, multi-user state, images, Box questions, long context.

## Stations

Each station is one screen with the same three-part layout (see Interface). Each lists
the baseline regex, the Jev questions, the presets, and what the presenter says.

### 1. Intent — "What does this customer want?"

- **Primitive:** one Choice.
- **Regex baseline:** an ordered keyword ladder, first match wins:
  ```
  refund     /\b(refund|money back|reimburs\w*)\b/i
  cancel     /\b(cancel|unsubscribe|close my account)\b/i
  complaint  /\b(broken|damaged|terrible|worst|unacceptable|useless|complain\w*)\b/i
  question   /\?\s*$|\b(how|when|where|can i|do you)\b/i
  praise     /\b(thanks|thank you|love|great)\b/i
  ```
- **Jev question:**
  ```ts
  intent: choice("What does the customer want from this email?", {
    refund:    "Wants money back now, for a purchase",
    exchange:  "Wants a replacement or a different item, not money back",
    cancel:    "Wants to stop a subscription, order or account",
    complaint: "Reports a problem or is unhappy, without asking for a specific remedy",
    question:  "Asks for information; no problem and no remedy requested",
    praise:    "Thanks or compliments; no action needed",
    other:     "None of the above",
  })
  ```
- **Presets** (each one breaks the regex for a different reason; the "Regex says" column
  is the output of the ladder above, checked by running it):
  | Email | Gold | Regex says | Why it fails |
  |---|---|---|---|
  | "The refund came through yesterday, thanks!" | praise | refund | past tense, already resolved |
  | "Give me back what I paid, this thing is useless." | refund | complaint | synonym, no keyword |
  | "I don't want a refund, just send one that works." | exchange | refund | negation |
  | "Great, thanks for shipping it to the wrong city." | complaint | praise | sarcasm |
  | "Can I get my money back if it's still sealed?" | question | refund | a policy question, not a request |
  | "Please don't cancel my subscription, I only wanted to know when it renews." | question | cancel | negation |
  | "pls refnd order 4471" | refund | none | misspelling |

  Jev's answers for these are not known yet; they are recorded, not assumed (see Data).
- **Presenter line:** "Each regex fix adds a rule that breaks another email."

### 2. Flags — several things can be true at once

- **Primitive:** one Noul per flag, in one request (Noul has no `confidence`; the value is
  the probability of yes).
- **Flags:** `asks_refund_now`, `wants_human`, `repeat_contact`, `legal_or_chargeback_threat`,
  `cancellation_risk`.
- **Regex baseline:** one pattern per flag, e.g. `wants_human: /\b(human|agent|real person|manager)\b/i`,
  `legal: /\b(lawyer|sue|legal|chargeback)\b/i`.
- **Presets:** "Are you a bot?" (lands in the unsure middle: 0.32), "I'm not a lawyer,
  but charging me again… Please reverse it." (regex fires on `lawyer`, misses the refund),
  "Third time writing about this" (repeat contact with no keyword), "My manager asked me to
  order 40 more" (regex fires on `manager`).
- **Shows:** a per-flag threshold pair (`no < p < yes` = review band). Moving the sliders
  re-colours the results without a new request.

### 3. Triage — route with confidence gating

- **Primitives:** Choice `department` (returns / shipping / billing / account / other),
  Score `urgency` (3 described levels), and speculative branch Choices asked in the same
  request (`return_reason`, `shipping_issue`), as in the
  [Choice docs](https://docs.typesafe.ai/primitives/choice.md) triage example. Code reads
  only the branch that applies.
- **Regex baseline:** a routing table of `if /pattern/ → queue`.
- **Shows a three-way outcome:** auto-route (high confidence), copy a second team (runner-up
  probability above a threshold), send to manual triage (low confidence). The UI draws
  the department probability bars and the code path taken.
- **Presets:** a billing complaint that mentions a delivery ("charged twice for a package
  that never came"), a calm email that is urgent ("the wedding is Saturday"), an angry email
  that is not, and an exchange with no routing keyword ("swap it for a large"). A routing
  table with no matching row falls through to `other`, as the corpus rubric scores it.

### 4. Keep your regex — regex proposes, Jev picks

- **Primitive:** Choice whose options are the regex's matches plus `none`
  ([pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md)).
- **Cases:**
  - Order ID: "Orders A-1182 and A-1190 arrived. A-1182 is fine but the lamp in A-1190 is
    cracked." → which order to refund. Regex `/\bA-\d{3,}\b/g` finds both.
  - Amount: an invoice with subtotal, tax, discount and total → the amount charged. Regex
    finds every money string.
  - Email address: "send the receipt to my work address, not the gmail" → which address.
- **Shows:** the regex matches highlighted in the text (blue), Jev's pick (red) with its
  probability, and the value copied unchanged from the text. Point out: the answer is always
  one of the highlighted spans.
- **Choice limit:** at most 255 options; presets stay far below.

### 5. Scan a long email — which sentences need action

- **Primitive:** one Noul per sentence, all in one request. Sentences come from a simple
  splitter in code.
- **Regex baseline:** sentences matching a "problem words" pattern.
- **Shows:** the ex-regex scan view: every sentence with its probability bar, a threshold
  slider, matching sentences highlighted. Preset: the mixed ticket (thanks + wrong charger +
  request + FYI + complaint + praise).

### 6. Scoreboard — both, over the whole corpus

- Runs every station's regex and recorded Jev answers over the labelled corpus (see Data).
- Shows accuracy per station for regex and Jev, and a **disagreements** list: only the
  emails where regex and Jev differ, with the gold label. This is the "audit your existing
  regex" beat.
- A "Paste your regex" box lets a viewer replace the baseline pattern and see the
  regex score recompute in the browser (Jev answers are already recorded).

### Optional stations (after the core six)

- **Moderation:** a profanity regex vs meaning (the Scunthorpe problem, quoted insults,
  reclaimed words).
- **Redaction:** redact a person's contact details but keep the company support address.
  This is ex-regex's headline example; add only if a non-support beat is needed.

### "When to keep the regex" card

A static card shown at the end of guided mode: use a regex or code for format validation,
exact IDs, counting and arithmetic; use Jev for meaning; combine them as in station 4.

## Interface

Modelled on the ex-regex playground screenshot.

- **Top bar:** product name, mode pill (`Recorded` / `Live`), model ID in use, guided/free
  toggle.
- **Left nav:** stations grouped as *Classify* (1, 2, 3), *Extract* (4, 5), *Trust* (6).
- **Station header:** title, one-sentence explanation, preset chips.
- **Body, three columns on wide screens, stacked on narrow:**
  1. **Input:** editable email text. Ask button and `Ctrl+Enter`.
  2. **Regex:** the baseline pattern (editable), its verdict, matched text highlighted in
     the email. A red ✗ or green ✓ against the preset's gold label.
  3. **Jev:** answer, probability bars for every option or flag, threshold slider(s),
     the code path taken (for station 3), the same ✗/✓ badge.
- **Under the columns, collapsed by default:** "Request" (the exact JSON sent: state +
  questions), "Response" (raw answer JSON), and "Code" (the TypeScript SDK call, copyable).
- **Footer per answer:** model ID, input tokens, cost (input tokens × $0.042 per million,
  from the [models page](https://docs.typesafe.ai/models.md); output tokens are free),
  latency (live only; recorded answers show the latency measured when recorded).
- **Projector-friendly:** base font ≥ 18 px, a "presenter" zoom (`+`/`-`), high-contrast
  light theme matching the Streamlit demo's (`demo/.streamlit/config.toml`), no hover-only
  information.
- **Thresholds never re-ask:** moving a slider recomputes from stored probabilities.
- **Editable meaning (live mode):** in free play the Jev column's instructions and
  option descriptions are editable, the counterpart of editing the regex. Rewording
  re-asks Jev. In recorded mode they are locked to the recorded wording.

### Guided mode

- An ordered script of steps; each step = station + preset + optional highlighted element
  + speaker note.
- `→` / `←` move between steps; `N` shows speaker notes on the presenter's screen; `L`
  opens the live box ("type your own email").
- Default script (~5 min): 1 (refund came through) → 1 (negation) → 2 (are you a bot?) →
  3 (charged twice for missing package) → 4 (A-1190) → 6 (scoreboard) → keep-the-regex card
  → live box.

## Architecture

```
src/
  stations/        one module per station: regex baseline, buildQuestions(input),
                   interpret(answers, thresholds), presets, gold labels
  web/             React UI (reads stations/, never imports the SDK)
  server/          Node HTTP server: POST /api/ask, GET /api/health
  recordings/      recordings.jsonl (one line per recorded request/response)
scripts/
  record.ts        call Jev for every preset and corpus item missing a recording
  eval.ts          score regex vs Jev over the corpus, write eval/results.json
data/
  corpus.jsonl     labelled emails (see Data)
```

- **Station modules are shared** by the UI, the server and the scripts, so the request a
  viewer sees is the request that was recorded. They build questions as plain JSON
  (`{type: "choice", instructions, criteria}`) and import nothing from the SDK; only
  `server/` and `scripts/` import `TypeSafeClient`.
- **Question wording** for stations 2, 3 and 5 (Noul instructions, Score levels, the
  per-sentence Noul) is drafted and iterated during recording, written as what the writer
  does ("the customer asks, now, to get money back"), and frozen before the first corpus
  eval. The rubric rules behind the first misses were then copied into the wording (see the
  README's Measured results), so the corpus is no longer held out.
  Any wording change changes the recording key, so it means re-recording.
- **Recording key:** SHA-256 of `{model, state, questions}` in canonical JSON. A lookup
  miss in recorded mode shows "not recorded — switch to Live" rather than guessing.
- **Recording line:** `{key, model, request, response, latency_ms, recorded_at}`.
- **Recorded mode needs no server:** the build bundles `recordings.jsonl`, so recorded
  mode deploys as a static site.
- **Live mode:** the server builds the request from the station module. The browser sends
  `stationId`, the text, for station 4 the candidates, and any edited wording; the server
  keeps only edits to known questions and option descriptions. Guards: max input length
  (4,000 chars), a per-process request cap and a daily token cap from env, both shown in
  the UI when reached. SDK retries stay on.
- **Errors:** an API or network failure shows a typed error in the Jev column and leaves
  the regex column working; it never falls back to a fake answer.

## Data and evaluation

- `data/corpus.jsonl`: 25–40 authored emails per Classify station, each with a gold label
  and a note on why it is hard. Mix easy cases (where regex is right) with hard ones, so
  the scoreboard is not rigged.
- Write the labelling rubric before writing labels; a rule added later means relabelling.
- Record corpus items 3 times to measure repeat noise (intent: a 10-case pilot; flags and
  triage: every case), and report regex-vs-Jev differences against that noise: per task,
  the 95% upper bound of the rate at which that task's decision flips, applied to the
  task's decisions.
- Flags are scored with the screen's default review bands; a flag in the review band is
  counted as "to review", not as right or wrong.
- `eval/results.json` feeds the scoreboard; the README has a short "Measured results" table
  with the date and model ID, like ex-regex's.
- Presets in the UI should show the recorded answer, even when Jev gets one wrong. If a
  preset fails, keep it on the scoreboard and drop it from the guided script only if the
  story needs it — and say so in the README.

## Testing

- Unit tests (Vitest): each station's regex baseline and `interpret()` on fixed answers,
  threshold bands, the station-4 "answer is one of the candidates" invariant.
- Recording completeness: a test fails if any preset or corpus item lacks a recording for
  the configured model.
- Server: `/api/ask` with a stubbed SDK client; key absent → live mode reported unavailable.
- One Playwright smoke test: guided mode steps through the whole script in recorded mode
  with the network blocked.

## Done when

- `npm run dev` serves the app; with no key, every guided step renders from recordings.
- With `TYPESAFE_API_KEY` set, typing a new email in each station returns a live answer
  with tokens, cost and latency shown.
- `npm run eval` prints regex and Jev accuracy per station; the scoreboard shows the
  same numbers.
- `npm test` and the Playwright smoke test pass.
- The README states the model ID, recording date, measured results and the limits above.

## Open questions

1. Pin `jev-1.13.0` (stable) or `jev-1.14.0` (newest, preview)? Default is 1.13.0.
2. Hosting: static recorded-only site (GitHub Pages) plus a private live server, or one
   hosted app with live mode behind a password?
3. Language: English only, or add a Dutch preset set? (Check Jev's language support on
   the models page first.)
4. Branding: TypeSafe styling or neutral?
