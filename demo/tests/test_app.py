"""The Streamlit app renders every station from recordings, with no key."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
PAGES = [
    "stations/dq.py",
    "stations/er.py",
    "stations/schema.py",
    "stations/schema_noul.py",
    "stations/pii.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_from_recordings(page, monkeypatch):
    monkeypatch.delenv("JEV_MODE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.switch_page(page).run()
    assert not at.exception
    assert at.title[0].value
    at.button[0].click().run()  # the preset in "Your turn" is recorded
    assert not at.exception
    assert not at.warning


def test_lessons_page_renders_the_doc():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.switch_page("lessons.py").run()
    assert not at.exception
    assert "# Lessons learned" in at.markdown[0].value
