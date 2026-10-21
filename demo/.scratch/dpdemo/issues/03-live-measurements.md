# 03: Live measurements

**What to build:** The three numbers the audience will ask for, measured with live calls
and written into `spec.md` under "Measured during the build": the maximum number of options
one Choice accepts, latency and throughput for ~100 rows with async batching, and cost per
question extrapolated to 1M rows from the usage the API reports. The throughput run is also
usable as a live moment in the talk (a timed cell).

**Blocked by:** 01

**Status:** done

- [x] Choice option cap found by live calls (largest accepted, smallest rejected, with the error text), or by a documented limit with its source
- [x] p50/p95 latency per call and rows/second for ~100 rows, with the concurrency used
- [x] Cost per question and per 1M rows, with the usage fields it was derived from
- [x] Numbers and the date measured are in `spec.md`
