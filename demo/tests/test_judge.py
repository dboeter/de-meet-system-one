import json

import pytest
from typesafe_sdk import Noul

from jevdemo.judge import Judge, LiveUnavailable, NotRecorded

STATE = {"value": "Damrak 1, 1012 LG Amsterdam"}
QUESTIONS = {"address": Noul(instructions="Is `value` a postal address?")}
RESPONSE = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 322, "output_tokens": 53},
    "answers": {"address": {"type": "noul", "noul": 0.98}},
}


class StubClient:
    def __init__(self):
        self.calls = []

    def system_one(self, state, questions, *, model):
        from typesafe_sdk import SystemOneResponse

        self.calls.append((state, questions, model))
        return SystemOneResponse.model_validate(RESPONSE)


def test_live_call_is_recorded_then_replayed(tmp_path):
    path = tmp_path / "recordings.jsonl"
    client = StubClient()
    live = Judge(mode="live", recordings=path, client=client, record=True)

    first = live.ask(STATE, QUESTIONS)
    assert first.response.nouls["address"].noul == 0.98
    assert first.source == "live"
    assert len(client.calls) == 1

    line = json.loads(path.read_text().splitlines()[0])
    assert set(line) == {
        "key",
        "model",
        "request",
        "response",
        "latency_ms",
        "recorded_at",
    }
    assert line["request"]["state"] == STATE

    replayed = Judge(mode="recorded", recordings=path).ask(STATE, QUESTIONS)
    assert replayed.response.nouls["address"].noul == 0.98
    assert replayed.source == "recorded"
    assert replayed.latency_ms == line["latency_ms"]


def test_recorded_miss_raises_instead_of_guessing(tmp_path):
    judge = Judge(mode="recorded", recordings=tmp_path / "recordings.jsonl")
    with pytest.raises(NotRecorded, match="switch to live"):
        judge.ask(STATE, QUESTIONS)


def test_changed_wording_is_a_miss(tmp_path):
    path = tmp_path / "recordings.jsonl"
    Judge(mode="live", recordings=path, client=StubClient(), record=True).ask(
        STATE, QUESTIONS
    )
    reworded = {"address": Noul(instructions="Is `value` a street address?")}
    with pytest.raises(NotRecorded):
        Judge(mode="recorded", recordings=path).ask(STATE, reworded)


def test_live_without_record_flag_writes_nothing(tmp_path):
    path = tmp_path / "recordings.jsonl"
    Judge(mode="live", recordings=path, client=StubClient()).ask(STATE, QUESTIONS)
    assert not path.exists()


def test_live_without_key_is_reported_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("jevdemo.judge.ENV_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(LiveUnavailable, match="unavailable"):
        Judge(mode="live", recordings=tmp_path / "r.jsonl").ask(STATE, QUESTIONS)


class SlowEchoClient:
    """Answers p = the state's `p`, slower for earlier requests, so completion order differs from input order."""

    def system_one(self, state, questions, *, model):
        import time

        from typesafe_sdk import SystemOneResponse

        time.sleep(0.05 * (1 - state["p"]))
        answers = {"address": {"type": "noul", "noul": state["p"]}}
        return SystemOneResponse.model_validate({**RESPONSE, "answers": answers})


def test_ask_many_keeps_order_and_records_every_answer(tmp_path):
    path = tmp_path / "recordings.jsonl"
    requests = [({"p": p}, QUESTIONS) for p in (0.1, 0.4, 0.7, 0.9)]
    live = Judge(mode="live", recordings=path, client=SlowEchoClient(), record=True)

    answers = live.ask_many(requests, concurrency=4)

    assert [a.response.nouls["address"].noul for a in answers] == [0.1, 0.4, 0.7, 0.9]
    assert len(path.read_text().splitlines()) == 4
    replayed = Judge(mode="recorded", recordings=path).ask_many(requests)
    assert [a.response.nouls["address"].noul for a in replayed] == [0.1, 0.4, 0.7, 0.9]
    assert {a.source for a in replayed} == {"recorded"}
