# 01: Tracer bullet: one DQ check, recorded and live

**What to build:** A presenter opens the DQ notebook and runs it top to bottom with no API
key: ~30 synthetic silver-layer rows, the `address` check ("is a postal address: street +
number, optionally postcode/city") asked as one Noul per distinct value, every answer
replayed from a recording, and a threshold table that splits rows into auto-accept, reject
and review. With the key set, a live cell answers a value typed by the audience. This is the
single path to the API that every later station reuses (see `spec.md`, Record / replay).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Recording key is SHA-256 of `{model, state, questions}` in canonical JSON; a recording line holds `{key, model, request, response, latency_ms, recorded_at}`
- [x] Recorded mode with a missing key raises "not recorded — switch to live"; it never guesses
- [x] Live mode reads the key from `demo/.env`; no key → live reported unavailable
- [x] The model ID is pinned in one config value
- [x] A record script records every row of the station that lacks a recording
- [x] Synthetic data includes at least one phone number in `address` and one value Jev gets wrong (shown as recorded, lands in review or the wrong bucket)
- [x] Tests pass: recorded hit, recorded miss raises, live path with a stubbed client, threshold → bucket
- [x] A recording-completeness test fails when any row of the notebook lacks a recording for the pinned model
- [x] A notebook smoke test executes the DQ notebook in recorded mode with no key and passes
