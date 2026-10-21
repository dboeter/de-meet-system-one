# 06: Scan station

Spec: `docs/spec.md` (station 5).

**What to build:** A long email is split into sentences in code; one request asks a Noul
per sentence ("needs action from support"). Each sentence shows its probability bar; a
threshold slider highlights the ones above it, without a new request. The regex column
highlights sentences matching a "problem words" pattern. Preset: the mixed ticket.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The mixed-ticket preset is recorded and renders in Recorded mode
- [ ] Every sentence appears once, in order, with its probability
- [ ] Moving the threshold sends no request
- [ ] Unit tests cover the sentence splitter and the regex
