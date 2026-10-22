# Jev for Data Engineers — pipeline demo

A presentation demo for Digital Power colleagues (Data Engineering). It shows the four use
cases from `docs/use-cases.md` as
pipeline stations that call the TypeSafe API. Every answer can run live or replay a
recording, so the talk works with or without network.

## Decisions

| Topic | Decision |
|---|---|
| Stack | Python notebooks (Jupyter locally, pasteable into Databricks) plus a small `jevdemo` package. SDK: `typesafe-sdk` (sync `TypeSafeClient`; batches run on a thread pool because notebooks already run an event loop). |
| Answers | Recorded by default. `JEV_MODE=live` calls the API; `scripts/record.py` calls live and appends every missing answer. A recorded-mode miss raises "not recorded — switch to live", never guesses. |
| Model | Pinned versioned ID in one config value. Recordings store the `model` the response returned. |
| Data | Synthetic only, said on the first slide. The data-residency question in the use-case spec blocks client data. |
| Order | Presentation order, not the spec's build order: DQ → entity resolution → schema mapping → PII. Simple to high-stakes; PII closes on the residency gate. |
| PII depth | Short station here; link to the jevex demo for depth instead of rebuilding it. |

## Station skeleton

Every station has the same shape, so the audience learns it once:

```
synthetic rows → code step (normalize / block / regex / shortlist / dedupe)
              → rows settled by rules go straight to a bucket
              → ambiguous rows: Jev request (shown as JSON) → probability
              → threshold table (hi / lo) → auto-accept | reject | review
```

- The threshold table is the centre of each station, not Jev's answer: show counts per
  bucket and let the thresholds be changed in a cell (recompute is local, no new calls).
- Each station shows where Jev is wrong or unsure and where those rows land. Data is not
  tuned to force a wrong answer: where Jev gets none wrong on a set (stations 1, 2 and
  4 on the current data), the review queue or the extra flags are the story. Presets show the recorded answer even when it is wrong.
- Each station ends with a live cell where the room supplies an input.

## Stations

### 1. Semantic DQ (silver layer)

- **Data:** ~30 rows with `address`, `product_description`, `cancel_reason`. Seeds: a phone
  number in `address`, `zie mail` in `product_description`, free-text cancel reasons.
- **Code:** a YAML check config (plain-language check, threshold, action
  `warn | quarantine | fail_run`); distinct values first; cache by `(check_id, value_hash)`.
- **Jev:** one Noul per distinct value per check; a Choice over the code list plus
  `other/none` for `cancel_reason`.
- **Prompt variants:** `checks_variants.yaml` keeps wordings that did worse, same ids, compared
  in the notebook. The address check asks for one specific building with its own house
  number; the previous wording (an address's parts, postcode/city optional) had its lowest
  true row at 0.68 instead of 0.87 and 5 review rows instead of 3. Splitting the cancel check
  into a pass Noul plus a code Choice: review 1 → 7 rows, lowest true row 0.94 → 0.67;
  `1 - p(other)` stays.
- **Output:** per-row pass probability and flag, quarantine table, run-manifest fail rate;
  one column crosses its threshold and `fail_run` fires. Show cache hits on a rerun.
- **Live input:** a value plus a plain-language check.

### 2. Entity resolution

- **Data:** two small supplier tables (~25 records each). Seeds: `Gem. Amsterdam` vs
  `Gemeente Amsterdam, afd. Inkoop`; two different `Jansen B.V.` companies; a renamed company.
- **Code:** normalize, block on postcode / KvK prefix / phonetic key, exact rule on KvK or
  IBAN.
- **Jev:** one Noul per remaining pair; state `{a, b}` as named JSON; criteria cover
  subsidiaries, departments and name changes.
- **Output:** `(id_a, id_b, p_same, decision)`, union-find clusters, and a Levenshtein
  baseline on the same pairs with precision/recall and review-queue size side by side.
- **Live input:** two records.

### 3. Schema mapping

- **Data:** ~20 legacy source columns (`KLT_NM_VOL`, …) with type, comment and 5–10
  synthetic sample values; a target model with descriptions.
- **Code:** shortlist targets per column from a declared table mapping (`KLANT` → `customer`,
  `ORDER` → `order`, `invoice`) and type compatibility; always add `none — no target
  equivalent`. Name similarity was dropped: Dutch abbreviations share almost no characters
  with English target names, so it would rank the right target low.
- **Jev:** one Choice per source column over the shortlist.
- **Output:** mapping table `(source_col, target_col | none, p)`; review flags for 1:1
  conflicts and low confidence; a generated dbt `sources.yml`.
- **Live input:** a column name, type and sample values.
- **Result on the synthetic set:** 80% top-1, 64% pre-filled
  correctly, no wrong pre-fill; below the 70% success target. Option descriptions leave out
  the target type and state carries the source system (`schema.SOURCE_SYSTEM`); the first
  version, with a `(type)` suffix and no source system, gave 76% top-1, 60% pre-filled and
  one wrong pre-fill (`ORD_BTW_BDR → none` at 0.86). Other question variants: generic
  context in the question (64%) and a companion Noul instead of the `none` option (36%). Shortlist recall is 100% by
  construction (every type-compatible column of the declared tables), so it measures the
  table mapping, not a ranking.
- **Prompt variants** (`schema.VARIANTS`, one run each): dropping the `(type)` suffix alone
  gives 64% pre-filled and removes the wrong pre-fill; the source system in state alone gives
  80% top-1 but 60% pre-filled.

### 4. PII screening

- **Data:** ~20 Dutch free-text notes. Seed: `mijn buurvrouw mevrouw de Vries heeft diabetes`.
- **Code:** regex with checksums for BSN, IBAN, phone, email; a hit flags the row and skips Jev.
- **Jev:** one request per row with five Nouls: private person name, health, financial
  situation, address, GDPR Art. 9 special category.
- **Output:** per-category probabilities, `contains_pii`, routing to masked / restricted /
  excluded. Closing slide: the residency gate; link to jevex.
- **Live input:** a Dutch sentence.

## Record / replay

- `Judge.ask(state, questions)` in `jevdemo/judge.py` is the only path to the API.
- Each station's requests are registered in `jevdemo/stations.py`, including the
  preset of its live cell, so the preset also answers offline.
- **Key:** SHA-256 of `{model, state, questions}` in canonical JSON. Any wording change
  changes the key and needs re-recording.
- **Line in `recordings.jsonl`:** `{key, model, request, response, latency_ms, recorded_at}`.
- **Live:** reads `TYPESAFE_API_KEY` from `demo/.env`; no key → live mode reported
  unavailable.
- **Recorded latency:** shown as measured at record time.
- `scripts/record.py` records every preset and data row that lacks a recording.

## Measured during the build

Not assumed; the audience will ask. Measured 2026-10-21 on `jev-1.13.0` with
`scripts/measure.py` (rerunnable on stage as the timed live moment).

- **Choice option cap: 255.** 255 options accepted; 256 rejected with `422 … criteria:
  Dictionary should have at most 255 items`. Matches docs.typesafe.ai/primitives/choice,
  which also advises sending the full option list rather than a shortlist. Station 3
  keeps a shortlist for relevance (one source table's target tables), not for size; the
  full-list variant is untested.
- **Latency:** p50 ~215 ms, p95 ~290 ms per call (one DQ Noul, ~320 input tokens).
- **Throughput (100 distinct values):** 4.3 rows/s sequential, 34 rows/s at 8 threads,
  65 rows/s at 16 threads; latency per call stays flat, so it scales with concurrency.
  Rate limits were not hit at 16.
- **Cost:** $0.042 per million input tokens, output free (docs.typesafe.ai/models).
  ~320 `usage.input_tokens` per question → ~$0.0000134 per question, ~$13 per 1M
  questions. A DQ row with 3 checks is 3 questions (~$40 per 1M rows), before
  deduplication; on station 1 deduplication cut 90 cells to 73 calls.

## Layout

```
demo/
  spec.md
  jevdemo/judge.py        record/replay client
  jevdemo/pipeline.py     thresholds, buckets, union-find, manifest
  jevdemo/stations.py     every station's requests (record script, completeness test)
  jevdemo/dq.py …         one module per station
  data/*.csv              synthetic sets per station
  checks.yaml             DQ check config
  checks_variants.yaml    DQ check wordings that did worse, kept for comparison
  recordings.jsonl
  notebooks/01_dq.ipynb … 04_pii.ipynb
  notebooks/05_lessons.ipynb  question-wording experiments, recomputed from recordings
  app/streamlit_app.py    Streamlit twin of the notebooks, same package and recordings (`uv run streamlit run app/streamlit_app.py`)
  .streamlit/config.toml  its theme
  scripts/record.py
  tests/
```

## Tests

- `judge`: recorded hit, recorded miss raises, live path with a stubbed client.
- Pipeline: thresholds → buckets, union-find clusters, manifest fail rate.
- Recording completeness: fails if any preset or data row lacks a recording for the pinned model.
- All four notebooks execute top to bottom in recorded mode with no key (`nbclient`).
- The Streamlit app renders all four stations and their recorded live presets, and every guided step, with no key (`AppTest`).

## Done when

- With no key, all four notebooks run top to bottom from recordings.
- With the key set, each station's live cell returns an answer for new input.
- Latency, cost and Choice-cap numbers are filled into this spec.

## Source

Use cases: `docs/use-cases.md` (copied from the rm-rjev session scratchpad).
