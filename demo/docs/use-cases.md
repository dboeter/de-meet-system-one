# Jev use cases at Digital Power — short specs

Four candidates for Jev as a judgment step inside data engineering pipelines. Common rule
for all four: code finds the candidates, does the exact matching and owns the workflow.
Jev makes the semantic judgment, and its probability decides whether a row is
auto-accepted, rejected or sent to review.

Shared open questions (settle before any client pilot):

- **Data residency / DPA.** Client rows leave the platform for the TypeSafe API. Retention,
  hosting region and the processing agreement are not verified. This blocks spec 3 for real
  data and the others for personal data.
- **Throughput and cost.** Requests per second, batching and price per question at 1M+ rows
  are not verified; measure them in the pilot.
- **Integration.** Running it as a Databricks/Spark UDF (batched HTTP calls per partition)
  is assumed and has not been tested.

---

## 1. Entity resolution (record dedup and matching)

**Problem.** Customer, supplier and company master data from different sources holds
duplicates that rules miss ("Gem. Amsterdam" vs "Gemeente Amsterdam, afd. Inkoop") and
false matches that fuzzy matching creates (two different "Jansen B.V." companies).

**Input → output.** Two tables, or one table against itself → a match table
`(id_a, id_b, p_same, decision)` plus a cluster id per record.

**Design.**

1. Code: normalize the fields, then use blocking (postcode, KvK prefix, phonetic name key)
   to keep the candidate pairs to a manageable number.
2. Code: exact rules settle the obvious cases (same KvK number or IBAN → match).
3. Jev: one **Noul** per remaining pair. State is both records as named JSON. Question:
   "Do `a` and `b` refer to the same real-world organisation?" The criteria cover
   subsidiaries, departments and name changes.
4. Code: `p_same ≥ hi` → merge, `≤ lo` → keep separate, in between → review queue.
   Union-find turns the pairs into clusters.

**Evaluation.** Hand-label 300–500 pairs from one client dataset, taken from the band
where fuzzy-match scores are ambiguous. Compare against the current fuzzy threshold
(e.g. Splink or Levenshtein): precision and recall at the chosen thresholds, and the
size of the review queue.

**Success.** Recall at least as high as the current fuzzy matching, a review queue at
least 50% smaller, and precision ≥ 0.98 on auto-merges.

**Risks.** Blocking recall puts a ceiling on overall recall, because Jev can't match a
pair it never sees. Measure blocking recall separately.

---

## 2. Semantic data-quality checks (silver layer)

**Problem.** Data-quality tools check types, nulls and ranges. They can't tell that
`address` holds a phone number, that `product_description` says "zie mail", or that
`cancel_reason` is free text that should map to a code.

**Input → output.** A column plus a check definition (YAML) → per row a pass probability
and a flag. Per batch, the fail rate goes into the run manifest, and a quarantine table
holds the failing rows.

**Design.**

1. Config: per column, a check written in plain language, e.g. `address: "is a postal
   address (street + number, optionally postcode/city)"`, plus a threshold and an action
   (`warn` | `quarantine` | `fail_run`).
2. Code: deduplicate the values first (distinct values are usually far fewer than rows)
   and cache answers by `(check_id, value_hash)`.
3. Jev: one **Noul** per distinct value per check. Columns that need a code use a
   **Choice** over the code list instead, with an `other/none` option.
4. Code: write the results to the medallion run manifest. If the fail rate passes the
   threshold, the run fails closed.

**Evaluation.** Three columns from one client with 200 labelled values each, measured
against the existing regex/Great Expectations checks: the extra errors caught and the
false-alarm rate.

**Success.** A reusable package (`dq-semantic`) with a declarative config that runs on
Databricks. It needs a cache hit rate above 80% on reruns and catches at least one class
of error that the current checks miss.

**Risks.** Checks written loosely give vague answers. Ship a template and a small set of
example values for every check.

---

## 3. PII / GDPR screening of free text

**Problem.** Free-text fields (notes, complaints, call transcripts) end up in the
lakehouse with names, BSN, health or financial details inside. Regex finds the
structured identifiers (BSN, IBAN) but misses context: "mijn buurvrouw mevrouw de Vries
heeft diabetes".

**Input → output.** A text column → per row a probability for each PII category, and a
`contains_pii` flag that drives masking, a restricted table, or exclusion from gold.

**Design.**

1. Code: regex with checksums for BSN, IBAN, phone and email. A hit gives a definite
   flag and skips Jev.
2. Jev: one **Noul** per category on the rest. Categories: person name of a private
   individual, health info, financial situation, address, special-category data
   (GDPR Art. 9).
3. Code: if any category is above threshold, flag the row. Thresholds lean towards
   recall. Masking stays in code; Jev only says *whether*, not *where*. Locating the
   span is a later step (selecting from candidate spans).

**Evaluation.** Reuse the jevex demo as the baseline, then 500 labelled Dutch-language
rows from one client. Measure recall per category (the main metric) and precision against
regex alone and against Presidio.

**Success.** Recall on contextual PII ≥ 0.95 at a precision the data owners accept. The
false-negative examples get written up for the client's data-protection officer.

**Risks.** Sending text to an external API to *find* PII has to be cleared first (see
the shared data-residency question). Without that, this can only be demoed on synthetic
data.

---

## 6. Schema mapping for migrations

**Problem.** Migrating to a lakehouse or a new system means mapping hundreds of source
columns to a target model. Today that's spreadsheets and naming guesswork
(`KLT_NM_VOL` → `customer.full_name`?).

**Input → output.** Source schema (names, types, comments, sample values) plus target
model → a mapping table `(source_col, target_col | none, p, confidence)` for a consultant
to review.

**Design.**

1. Code: shortlist roughly 5–15 target candidates per source column using type
   compatibility and name/description similarity. Always add `none — no target
   equivalent`.
2. Jev: one **Choice** per source column over the shortlist. State is the source column
   name, type, comment and 5–10 sample values, plus each candidate's name and
   description.
3. Code: if confidence is high and nothing conflicts, pre-fill the mapping. When two
   source columns map to the same 1:1 target, or confidence is low, send them to review.
   The output is a spreadsheet or dbt `sources.yml` that the consultant approves.

**Evaluation.** One completed past migration where the final mapping is the gold set.
Measure top-1 accuracy, shortlist recall (whether the right target was in the shortlist),
and how often `none` was right.

**Success.** At least 70% of columns pre-filled correctly and a measurable cut in hours
spent mapping on the next migration.

**Risks.** The shortlist caps accuracy (measure it separately). Sample values may hold
PII, so mask them or use synthetic samples when the data-residency question isn't settled.
I haven't verified the maximum number of options in one Choice, so check it before
skipping the shortlist step.

---

## Suggested order

1. **Spec 2 (DQ checks)**: simplest to build, reusable everywhere, and it fits the
   existing medallion pipeline pattern.
2. **Spec 1 (entity resolution)**: has the clearest business value and a baseline to beat.
3. **Spec 6 (schema mapping)**: needs a past migration as gold, then it's cheap to test.
4. **Spec 3 (PII)**: has the highest value but is gated on the data-residency question.
   Start with the synthetic jevex demo.
