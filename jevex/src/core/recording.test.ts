import { describe, expect, it } from "vitest";
import type { JevRequest } from "./jev.ts";
import { canonicalJson, parseRecordings, recordingKey, RecordingStore, type Recording } from "./recording.ts";

const request: JevRequest = {
  model: "jev-1.13.0",
  state: "hello",
  questions: { q: { type: "noul", instructions: "Is it a greeting?" } },
};

const response = { model: "jev-1.13.0", answers: { q: { type: "noul", noul: 0.97 } }, usage: { input_tokens: 10, output_tokens: 2 } };

function line(key: string, repeat: number, noul = 0.97): string {
  return JSON.stringify({
    key,
    repeat,
    model: "jev-1.13.0",
    request,
    response: { ...response, answers: { q: { type: "noul", noul } } },
    latency_ms: 300,
    recorded_at: "2026-10-20T00:00:00.000Z",
  });
}

describe("canonicalJson", () => {
  it("sorts object keys at every depth", () => {
    expect(canonicalJson({ b: 1, a: { d: [2, { z: 1, y: 2 }], c: null } })).toBe(
      '{"a":{"c":null,"d":[2,{"y":2,"z":1}]},"b":1}',
    );
  });
});

describe("recordingKey", () => {
  it("is the SHA-256 hex of the canonical request and ignores key order", async () => {
    const reordered: JevRequest = { questions: request.questions, state: "hello", model: "jev-1.13.0" };
    const key = await recordingKey(request);
    expect(key).toMatch(/^[0-9a-f]{64}$/);
    expect(await recordingKey(reordered)).toBe(key);
  });

  it("changes when the wording changes", async () => {
    const reworded: JevRequest = { ...request, questions: { q: { type: "noul", instructions: "Is it hello?" } } };
    expect(await recordingKey(reworded)).not.toBe(await recordingKey(request));
  });
});

describe("RecordingStore", () => {
  it("looks up a recording by key and repeat", () => {
    const store = new RecordingStore(parseRecordings(`${line("k1", 0)}\n${line("k1", 1, 0.9)}\n`));
    expect(store.get("k1")?.response.answers.q).toEqual({ type: "noul", noul: 0.97 });
    expect(store.get("k1", 1)?.response.answers.q).toEqual({ type: "noul", noul: 0.9 });
    expect(store.get("missing")).toBeUndefined();
    expect(store.repeats("k1").length).toBe(2);
  });

  it("rejects a malformed line with its line number", () => {
    expect(() => parseRecordings(`${line("k1", 0)}\n{"key":"x"}`)).toThrow(/line 2/);
  });

  it("adds recordings and serialises them as one JSON line each", () => {
    const store = new RecordingStore([]);
    const [rec] = parseRecordings(line("k2", 0));
    store.add(rec as Recording);
    expect(store.toJsonl()).toBe(`${line("k2", 0)}\n`);
  });
});
