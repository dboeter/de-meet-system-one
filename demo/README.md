# Jev for Data Engineers

A presentation demo of four pipeline stations where code handles the clear-cut rows and Jev (TypeSafe's
System One model) judges the ambiguous ones. Each answer is a probability, and a threshold table turns it
into accept, review or reject. All data is synthetic.

| Station | Code step | Jev's question |
|---|---|---|
| Semantic data quality | YAML checks, distinct values, cache | Does this value pass the check? Which cancel code is this? |
| Entity resolution | Normalize, block, exact KvK/IBAN rule | Are these two suppliers the same organisation? |
| Schema mapping | Shortlist targets by table and type | Which target column holds this source column's data? |
| PII screening | Regex with checksums (BSN, IBAN, phone, email) | Does this note name a person, or reveal health, finances, an address or Art. 9 data? |

The same stations come in two forms, so you can compare them:

- **Notebooks** (`notebooks/01_dq.ipynb` … `04_pii.ipynb`): the step-by-step story with the code visible. `05_lessons.ipynb` recomputes the question-wording experiments.
- **Streamlit app** (`app/`): a Guided walkthrough to present from, then an overview and one page per station
  for questions. The walkthrough has 13 steps, each example first. Move with Back/Next, the arrow keys or a
  clicker's PageUp/PageDown, and open a step directly with `?step=N`. Each station page shows the result,
  threshold sliders, tables, the requests Jev receives and a form for live input.

Both use the `jevdemo` package and `recordings.jsonl`, so they show the same numbers.

## Setup

Needs Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Run

```bash
# Streamlit app, at http://localhost:8501 (the walkthrough is at /guided)
uv run streamlit run app/streamlit_app.py

# Notebooks: open them in VS Code with the .venv kernel, or
uv run --with jupyterlab jupyter lab notebooks/
```

## Recorded or live

By default every answer is replayed from `recordings.jsonl`, so the demo runs without network or key.
A request that was never recorded fails with "not recorded — switch to live" and never guesses.

To call the API, put a key in `demo/.env`:

```
TYPESAFE_API_KEY=...
```

- **Notebooks:** start Jupyter with `JEV_MODE=live`.
- **App:** use the "Live API calls" toggle in the sidebar. It is disabled when no key is found. The app
  ignores `JEV_MODE`. A live answer stays cached until the server restarts.

Each station's live input has a recorded preset, so it also answers offline. Any other input needs live mode.

## Scripts

```bash
uv run python scripts/record.py    # call live for every request that lacks a recording, and append it
uv run python scripts/measure.py   # latency, throughput, cost and the Choice option cap (live, not recorded)
```

A recording's key is a hash of the model, state and question wording, so changing a question means
running `record.py` again.

## Tests

```bash
uv run pytest
```

The tests run with no key. They check that every request has a recording, that all five notebooks run
top to bottom, and that every app page renders, including its live preset.

## More

- `spec.md`: decisions, the station designs, and what was measured during the build.
- `docs/use-cases.md`: the use cases the stations come from.
- `docs/lessons-learned.md`: what changing the question wording did, and what we learned (also a page in the app).
- `checks.yaml`: the DQ checks, written as config in plain language.
- `checks_variants.yaml`: prompt variants of those checks, compared in `01_dq.ipynb`.
