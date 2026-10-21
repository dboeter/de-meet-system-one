# 05: Schema mapping station

**What to build:** `spec.md` station 3. ~20 legacy source columns (`KLT_NM_VOL`, …) with
type, comment and 5–10 synthetic sample values, against a target model with descriptions.
Code shortlists targets per column (type compatibility, name similarity) and always adds
`none — no target equivalent`; Jev answers one Choice per column. The notebook shows the
mapping table, flags 1:1 conflicts and low confidence for review, and writes a dbt
`sources.yml` a consultant would approve. A live cell takes a column name, type and samples.

**Blocked by:** 01, 03 (shortlist size depends on the measured Choice option cap)

**Status:** done

- [x] Shortlist size stays within the measured Choice cap
- [x] Mapping table `(source_col, target_col | none, p)` with review flags
- [x] Hand-made gold mapping; top-1 accuracy, shortlist recall and `none` accuracy reported
- [x] Generated `sources.yml` is valid YAML and contains only non-review mappings
- [x] Recording completeness and notebook smoke tests cover this notebook and pass with no key
