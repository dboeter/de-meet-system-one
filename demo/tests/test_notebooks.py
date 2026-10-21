from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

NOTEBOOKS = sorted(
    (Path(__file__).resolve().parent.parent / "notebooks").glob("*.ipynb")
)


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_runs_from_recordings(path, monkeypatch):
    monkeypatch.delenv("JEV_MODE", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    nb = nbformat.read(path, as_version=4)
    NotebookClient(
        nb, timeout=60, resources={"metadata": {"path": str(path.parent)}}
    ).execute()
