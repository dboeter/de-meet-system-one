# 04: Entity resolution station

**What to build:** `spec.md` station 2. Two synthetic supplier tables (~25 records each)
seeded with `Gem. Amsterdam` vs `Gemeente Amsterdam, afd. Inkoop`, two different
`Jansen B.V.` companies and a renamed company. Code normalizes, blocks (postcode, KvK
prefix, phonetic name key) and settles same-KvK/IBAN pairs; Jev answers one Noul per
remaining pair ("Do `a` and `b` refer to the same real-world organisation?", criteria cover
subsidiaries, departments, name changes). The notebook shows the match table, union-find
clusters, and a Levenshtein baseline on the same pairs side by side. A live cell takes two
records from the audience.

**Blocked by:** 01

**Status:** done

- [x] Match table `(id_a, id_b, p_same, decision)` and a cluster id per record
- [x] Hand labels for the synthetic pairs; precision, recall and review-queue size for Jev and Levenshtein at the chosen thresholds
- [x] Pairs settled by exact rules never reach Jev
- [x] At least one wrong Jev answer is shown with where it lands — not met: Jev got none wrong / missed none on this set; the review queue (04) and extra flags (06) are shown instead, per the spec decision of 2026-10-21
- [x] Recording completeness and notebook smoke tests cover this notebook and pass with no key
