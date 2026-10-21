# 02: Request, response, code and usage footer

Spec: `docs/spec.md` (Interface).

**What to build:** Under any station's columns, a viewer can expand "Request" (the exact
JSON sent: state and questions), "Response" (raw answer JSON) and "Code" (the TypeScript
SDK call, with a copy button). Every Jev answer has a footer with model ID, input tokens,
cost (input tokens × $0.042 per million; output tokens are free) and latency (live
latency, or the latency measured at recording time for recorded answers).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The three sections are collapsed by default and work on the Intent station in both modes
- [ ] The Request shown is byte-identical to the one recorded or sent
- [ ] The copied code runs against the API and returns the same answer shape
- [ ] The footer shows model ID, tokens, cost and latency for every answer
