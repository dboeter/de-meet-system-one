# 04: Triage station

Spec: `docs/spec.md` (station 3).

**What to build:** The Triage station routes an email the way a support system would. One
request asks a Choice `department` (returns / shipping / billing / account / other), a
Score `urgency` with three described levels, and speculative branch Choices
(`return_reason`, `shipping_issue`); code reads only the branch that applies. The regex
column runs a routing table. The Jev column draws department probability bars and
highlights the code path taken: auto-route, copy a second team (runner-up above a
threshold), or manual triage (low confidence).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The four spec presets are recorded and render in Recorded mode
- [ ] The path taken is visible and changes when the confidence / runner-up thresholds move, without a new request
- [ ] Unused branch answers are not shown as part of the decision
- [ ] Unit tests cover the routing table and the three-way gating logic
