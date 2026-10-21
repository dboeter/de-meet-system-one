import { describe, expect, it } from "vitest";
import type { IntentCase } from "./corpus.ts";
import type { Outcome, RunLine } from "./runs.ts";
import { percentile, summarize } from "./stats.ts";

const cases: IntentCase[] = [
  { id: "a", text: "refund please", gold: "refund", tags: ["easy"], note: "" },
  { id: "b", text: "hmm", gold: "question", tags: ["hard", "ambiguous"], note: "" },
];

function line(case_id: string, repeat: number, outcome: Outcome, latency_ms = 100, cold = false): RunLine {
  return {
    judge: "jev-test",
    case_id,
    repeat,
    cold,
    started_at: "2026-10-20T00:00:00.000Z",
    latency_ms,
    outcome,
    input_tokens: 100,
    output_tokens: 1,
    cost_usd: 0.0000042,
    request: null,
    raw_response: null,
  };
}

const answer = (label: string, goldP: number, gold: string): Outcome => ({
  kind: "answer",
  label,
  confidence: 0.9,
  probabilities: { [gold]: goldP },
});

describe("percentile", () => {
  it("uses nearest rank", () => {
    expect(percentile([5, 1, 3, 2, 4], 50)).toBe(3);
    expect(percentile([5, 1, 3, 2, 4], 95)).toBe(5);
    expect(percentile([], 50)).toBeNull();
  });
});

describe("summarize", () => {
  const s = summarize({
    cases,
    regex: (text) => (text.includes("refund") ? "refund" : "none"),
    lines: [
      line("a", 0, answer("refund", 0.9, "refund"), 900, true),
      line("a", 1, answer("refund", 0.7, "refund"), 100),
      line("b", 0, answer("other", 0.2, "question"), 200),
      line("b", 1, answer("question", 0.6, "question"), 300),
      line("b", 2, { kind: "error", message: "boom" }, 50),
    ],
  });

  it("counts accuracy over answered calls and leaves errors out", () => {
    expect(s.calls).toBe(5);
    expect(s.errors).toBe(1);
    expect(s.accuracy).toEqual({ hit: 3, n: 4 });
    expect(s.accuracyUnambiguous).toEqual({ hit: 2, n: 2 });
    expect(s.perRepeat).toEqual([
      { repeat: 0, accuracy: { hit: 1, n: 2 } },
      { repeat: 1, accuracy: { hit: 2, n: 2 } },
    ]);
  });

  it("measures repeat consistency per case", () => {
    expect(s.unanimous).toEqual({ hit: 1, n: 2 });
    expect(s.cases.find((c) => c.id === "a")?.goldProbSpread).toBeCloseTo(0.2);
    expect(s.cases.find((c) => c.id === "b")?.goldProbSpread).toBeCloseTo(0.4);
  });

  it("keeps the cold call out of warm latency", () => {
    expect(s.latencyCold).toEqual([900]);
    expect(s.latencyWarm.max).toBe(300);
  });

  it("scores the regex with none as other", () => {
    expect(s.regexAccuracy).toEqual({ hit: 1, n: 2 });
  });
});
