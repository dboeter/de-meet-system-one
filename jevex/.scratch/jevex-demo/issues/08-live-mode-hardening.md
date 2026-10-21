# 08: Live mode: editable meaning, guards and errors

Spec: `docs/spec.md` (Interface, Architecture).

**What to build:** In free play with Live mode on, a viewer can edit the Jev column's
instructions and option descriptions, the counterpart of editing the regex, and re-ask.
In Recorded mode the wording is locked. The server enforces a max input length (4,000
chars), a per-process request cap and a daily token cap from env, and the UI says when
one is reached. An API or network failure shows a typed error in the Jev column; the
regex column keeps working and nothing falls back to a fake answer. With no key, the
server reports Live as unavailable and the pill says so.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Edited wording is what the server sends (visible in the Request section once 02 lands)
- [ ] Each cap, when hit, shows a clear message and sends no request
- [ ] Server tests with a stubbed SDK client cover success, API error, and missing key
