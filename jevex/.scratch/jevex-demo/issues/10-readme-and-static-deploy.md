# 10: README and static deploy

Spec: `docs/spec.md` (Done when, Non-goals).

**What to build:** Someone new can run and trust the demo. The README covers running it
(recorded and live), recording and eval commands, a "Measured results" table with model
ID and recording date taken from the eval output, any preset left out of the guided
script because Jev got it wrong, and the limits (shape and counting tasks stay with
regex; thresholds are illustrative). A build produces a recorded-only static site that
needs no server.

**Blocked by:** 07, 09

**Status:** ready-for-agent

- [ ] The static build opens and runs the guided script with no server and no key
- [ ] The Measured results table matches `npm run eval`
- [ ] Following the README from a clean clone gets to a running demo
