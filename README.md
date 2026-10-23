# DE Meet: System One

Demos and slides from the Digital Power talk on Jev (TypeSafe's System One model) for data engineers.

## Start here: [`demo/`](demo/)

**Jev for Data Engineers** is the main demo. Four pipeline stations where code handles the clear-cut rows
and Jev judges the ambiguous ones: semantic data quality, entity resolution, schema mapping and PII screening.
It comes as a Streamlit app with a guided walkthrough and as notebooks, and runs offline from recordings.

```bash
cd demo
uv sync
uv run streamlit run app/streamlit_app.py   # walkthrough at http://localhost:8501/guided
```

Setup, live mode and tests are in [demo/README.md](demo/README.md).

## Also in this repo

| Folder | What it is | Status |
|---|---|---|
| [`jevex/`](jevex/) | Regex vs Jev on customer service email, a web demo with a guided presenter mode | Side demo |
| [`rm-rjev/`](rm-rjev/) | Jev vs Haiku and Luna as a Claude Code permission judge | Failed experiment, kept for reference |
| `System_One_Models_DIP_v3.pptx` | The slide deck | |

If you only look at one thing, look at `demo/`.

## Disclaimer

This repository was largely built with AI and is for demo purposes only.
All data in it is synthetic, generated with AI. Any resemblance to real people or organisations is coincidental.
