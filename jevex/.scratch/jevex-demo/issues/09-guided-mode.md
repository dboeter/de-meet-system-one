# 09: Guided mode and presenter polish

Spec: `docs/spec.md` (Guided mode, Interface, "When to keep the regex" card).

**What to build:** A presenter runs the five-minute story from the keyboard. The guided
script is an ordered list of steps (station + preset + optional highlighted element +
speaker note): Intent (refund came through) → Intent (negation) → Flags (are you a bot?)
→ Triage (charged twice for a missing package) → Keep your regex (A-1190) → Scoreboard →
"When to keep the regex" card → live box. `→`/`←` move, `N` toggles speaker notes, `L`
opens the live box. Add presenter zoom (`+`/`-`), base font ≥ 18 px, high-contrast dark
and light themes, and no hover-only information.

**Blocked by:** 02, 03, 04, 05, 07

**Status:** ready-for-agent

- [ ] The full script steps through in Recorded mode with no network
- [ ] A Playwright smoke test runs the whole script with the network blocked and passes
- [ ] Guided and free play show the same station screens
- [ ] Both themes are readable on a projector (checked by the person at rehearsal)
