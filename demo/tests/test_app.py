"""The Streamlit app renders every page from recordings, with no key, in presenter view and with every detail.

The guided walkthrough renders all 13 steps, and its step comes from the URL.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
PAGES = [
    "stations/dq.py",
    "stations/er.py",
    "stations/schema.py",
    "stations/pii.py",
]


@pytest.mark.parametrize("presenting", [True, False])
@pytest.mark.parametrize("page", PAGES)
def test_page_renders_from_recordings(page, presenting, monkeypatch):
    monkeypatch.delenv("JEV_MODE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.toggle(key="presenting").set_value(presenting).run()
    at.switch_page(page).run()
    assert not at.exception
    assert at.title[0].value
    assert bool(at.tabs) != presenting  # the tables are detail
    # The live input closes the page; PII adds its data-residency note after it.
    assert "Your turn" in [h.value for h in at.subheader][-2:]
    at.button[0].click().run()  # the preset in "Your turn" is recorded
    assert not at.exception
    assert not at.warning


def test_overview_links_every_station():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception
    assert at.title[0].value == "Code for the clear cases, Jev for the rest"
    assert len(at.get("page_link")) == len(PAGES) + 1  # plus Lessons learned


def test_lessons_page_renders_the_doc():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.toggle(key="presenting").set_value(False).run()
    at.switch_page("lessons.py").run()
    assert not at.exception
    assert at.title[0].value == "Lessons learned: question wording"
    assert any("What we learned" in m.value for m in at.markdown)


def open_guided(monkeypatch, step=None):
    monkeypatch.delenv("JEV_MODE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    if step is not None:
        at.query_params["step"] = step
    return at.switch_page("guided.py").run()


def position(at) -> str:
    """The `n / 13` in the eyebrow above every step."""
    return next(m.value for m in at.markdown if " / 13" in m.value).rsplit(" · ", 1)[1]


def test_guided_walks_all_thirteen_steps(monkeypatch):
    at = open_guided(monkeypatch)
    clicks = 0
    while True:
        assert not at.exception
        assert not at.warning
        assert position(at) == f"{clicks + 1} / 13"
        if at.button(key="guided-next").disabled:
            break
        at.button(key="guided-next").click().run()
        clicks += 1
    assert clicks == 12  # the README promises 13 steps


@pytest.mark.parametrize(("param", "shown"), [("6", 6), ("99", 13), ("abc", 1)])
def test_guided_step_comes_from_the_url(param, shown, monkeypatch):
    at = open_guided(monkeypatch, param)
    assert not at.exception
    assert position(at) == f"{shown} / 13"


def test_guided_your_turn_answers_the_preset_from_its_recording(monkeypatch):
    at = open_guided(monkeypatch, "13")
    at.button(key="guided-ask").click().run()  # the first button on the page is Back
    assert not at.exception
    assert not at.warning
    assert any(c.value.startswith("recorded · ") for c in at.caption)
