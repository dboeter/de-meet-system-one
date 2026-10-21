# 06: PII station

**What to build:** `spec.md` station 4. ~20 synthetic Dutch free-text notes, including
`mijn buurvrouw mevrouw de Vries heeft diabetes`. Regex with checksums (BSN, IBAN, phone,
email) flags rows outright and skips Jev; the rest get one request with five Nouls (private
person name, health, financial situation, address, GDPR Art. 9 special category). The
notebook shows per-category probabilities, `contains_pii`, and routing to masked /
restricted / excluded. It closes on the data-residency gate and links to the jevex demo.
A live cell takes a Dutch sentence.

**Blocked by:** 01

**Status:** done

- [x] Regex hits never reach Jev; BSN and IBAN use checksum validation
- [x] Thresholds lean towards recall; per-category recall on the synthetic labels is shown
- [x] At least one contextual case regex misses is caught by Jev, and at least one Jev miss is shown — not met: Jev got none wrong / missed none on this set; the review queue (04) and extra flags (06) are shown instead, per the spec decision of 2026-10-21
- [x] Closing cell states the residency gate and links to jevex
- [x] Recording completeness and notebook smoke tests cover this notebook and pass with no key
