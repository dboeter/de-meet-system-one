# 07: Labelled corpus, eval and scoreboard

Spec: `docs/spec.md` (station 6, Data and evaluation).

**What to build:** Claims are backed by data. Write the labelling rubric first, then
25–40 authored emails per Classify station (Intent, Flags, Triage) with gold labels and a
note on why each is hard, mixing easy cases where the regex is right. Record them; record
a pilot batch three times to measure repeat noise. `npm run eval` scores regex vs Jev per
station and writes the results the Scoreboard station reads. The Scoreboard shows
accuracy per station and a disagreements list (only emails where regex and Jev differ,
with the gold label). A "Paste your regex" box recomputes the regex score in the browser.

**Blocked by:** 01, 03, 04

**Status:** ready-for-agent

- [ ] Rubric is committed before any labels
- [ ] `npm run eval` prints regex and Jev accuracy per station and the repeat-noise figure
- [ ] The Scoreboard shows the same numbers as `npm run eval`
- [ ] Pasting a regex updates its score without any request
- [ ] A test fails if any preset or corpus item lacks a recording for the configured model
