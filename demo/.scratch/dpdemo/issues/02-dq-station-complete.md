# 02: DQ station complete

**What to build:** The DQ notebook becomes the full semantic-DQ station from `spec.md`
station 1. Checks are declared in a YAML config (plain-language check, threshold, action
`warn | quarantine | fail_run`) for `address`, `product_description` (catches `zie mail`)
and `cancel_reason` (a Choice over a code list plus `other/none`). Failing rows land in a
quarantine table, the batch fail rate goes into a run manifest, and one column crosses its
threshold so `fail_run` fires. A rerun shows cache hits. The presenter can change a
threshold in a cell and see the buckets recompute without new API calls.

**Blocked by:** 01

**Status:** done

- [x] Distinct values are asked once; answers cached by `(check_id, value_hash)`; a rerun reports the cache hit rate
- [x] `cancel_reason` uses a Choice with an `other/none` option
- [x] The run manifest shows per-check fail rate and the `fail_run` outcome
- [x] Threshold changes recompute buckets locally with zero API calls
- [x] Recording completeness and notebook smoke tests pass with no key
