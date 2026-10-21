"""The single path to the TypeSafe API: live calls, or replay of recorded answers."""

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from typesafe_sdk import SystemOneResponse

MODEL = "jev-1.13.0"
ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = ROOT / "recordings.jsonl"
ENV_FILE = ROOT / ".env"

Mode = Literal["recorded", "live"]


class NotRecorded(LookupError):
    pass


class LiveUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Answer:
    response: SystemOneResponse
    latency_ms: int
    source: Mode


def request_body(state, questions) -> dict:
    return {
        "model": MODEL,
        "state": state,
        "questions": {
            name: q.model_dump(mode="json", exclude_none=True)
            for name, q in questions.items()
        },
    }


def recording_key(body: dict) -> str:
    # Canonical JSON: any change to model, state or question wording is a new key.
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_recordings(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    entries = (
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    )
    return {entry["key"]: entry for entry in entries}


def default_mode() -> Mode:
    return "live" if os.environ.get("JEV_MODE") == "live" else "recorded"


class Judge:
    def __init__(
        self,
        mode: Mode | None = None,
        recordings: Path = RECORDINGS,
        client=None,
        record=False,
    ):
        self.mode = mode or default_mode()
        self.path = Path(recordings)
        self.record = record
        self._client = client
        self._recordings = load_recordings(self.path)
        self._lock = threading.Lock()

    def has(self, state, questions) -> bool:
        return recording_key(request_body(state, questions)) in self._recordings

    def ask(self, state, questions) -> Answer:
        body = request_body(state, questions)
        key = recording_key(body)
        if self.mode == "recorded":
            entry = self._recordings.get(key)
            if entry is None:
                raise NotRecorded(f"not recorded — switch to live (key {key[:12]})")
            return Answer(
                SystemOneResponse.model_validate(entry["response"]),
                entry["latency_ms"],
                "recorded",
            )

        start = time.perf_counter()
        response = self.client.system_one(state, questions, model=body["model"])
        latency_ms = round((time.perf_counter() - start) * 1000)
        if self.record:
            self._append(key, body, response, latency_ms)
        return Answer(response, latency_ms, "live")

    def ask_many(self, requests, concurrency: int = 8) -> list[Answer]:
        """Answers in input order. Threads, not asyncio: notebooks already run an event loop."""
        if self.mode == "live":
            _ = self.client  # create the client once, before the threads race for it
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            return list(pool.map(lambda r: self.ask(*r), requests))

    @property
    def client(self):
        if self._client is None:
            from dotenv import load_dotenv
            from typesafe_sdk import TypeSafeClient

            load_dotenv(ENV_FILE)
            if not os.environ.get("TYPESAFE_API_KEY"):
                raise LiveUnavailable(
                    "live mode unavailable: TYPESAFE_API_KEY not set (demo/.env)"
                )
            self._client = TypeSafeClient()
        return self._client

    def _append(self, key, body, response, latency_ms):
        entry = {
            "key": key,
            "model": response.model,
            "request": body,
            "response": response.model_dump(mode="json"),
            "latency_ms": latency_ms,
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        with self._lock, self.path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._recordings[key] = entry
