# 03: Flags station

Spec: `docs/spec.md` (station 2).

**What to build:** The Flags station shows that several things can be true of one email.
One request asks five Nouls (`asks_refund_now`, `wants_human`, `repeat_contact`,
`legal_or_chargeback_threat`, `cancellation_risk`); the regex column runs one pattern
per flag. Each flag has a yes/no threshold pair; values between them show as "review".
Moving a slider re-colours the results without a new request. Noul wording is drafted
as what the writer does and iterated during recording.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The four spec presets are recorded and render in Recorded mode
- [ ] Each flag shows regex verdict, Jev probability, and yes / review / no from its threshold pair
- [ ] Moving a threshold sends no request
- [ ] Unit tests cover the per-flag regexes and the threshold bands
