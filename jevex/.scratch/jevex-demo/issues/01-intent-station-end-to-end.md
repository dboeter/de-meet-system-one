# 01: Intent station, end to end

Spec: `docs/spec.md` (station 1, Interface, Architecture).

**What to build:** A presenter opens the app and sees the Intent station: the shell
(top bar with Recorded/Live pill and model ID, left nav, station header with preset
chips) and the three columns. Picking a preset shows the email, the keyword-ladder regex
verdict with matched text highlighted, and Jev's Choice answer with a probability bar
per option, each with a ✓/✗ against the preset's gold label. With no API key everything
replays from recordings; with `TYPESAFE_API_KEY` set on the server, the Live toggle sends
typed text to Jev and shows the answer.

This ticket lays the shared foundations the other stations reuse: TypeScript project
(Vite + React front end, small Node server, `@typesafe-ai/sdk` 0.7.0 on the server only),
station modules that build questions as plain JSON and are shared by UI, server and
scripts, the recording format and key (SHA-256 of canonical `{model, state, questions}`),
and the record script. The model is one pinned config value, default `jev-1.13.0`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] With no key, `npm run dev` serves the Intent station and all seven presets render recorded answers
- [ ] A preset with no recording shows "not recorded — switch to Live", never a guessed answer
- [ ] With a key, typing a new email in Live mode returns a Jev answer through the server; the key never reaches the browser
- [ ] The record script records only presets missing a recording for the configured model
- [ ] The "Regex says" outputs match the spec's preset table
- [ ] Unit tests cover the regex ladder and the intent `interpret()` on fixed answers
