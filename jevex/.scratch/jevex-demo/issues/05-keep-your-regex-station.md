# 05: Keep-your-regex station

Spec: `docs/spec.md` (station 4).

**What to build:** The station shows regex and Jev working together. A regex finds every
candidate (order IDs, money amounts, email addresses) and highlights them in blue; one
Choice whose options are those candidates plus `none` picks the one the question asks
for, highlighted in red with its probability. The value shown is copied unchanged from
the text. Three presets: the order to refund, the amount charged on an invoice, the
address the receipt should go to.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The three presets are recorded and render in Recorded mode
- [ ] In Live mode the browser sends the candidates; the server builds the Choice from them
- [ ] A test asserts the answer is always one of the candidates or `none`
- [ ] With zero candidates the station says so and does not call Jev
