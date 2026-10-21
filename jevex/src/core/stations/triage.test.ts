import { describe, expect, it } from "vitest";
import type { JevResponse } from "../jev.ts";
import { rulesOrThrow } from "../regex.ts";
import { route, triage, triageRegex } from "./triage.ts";

const rules = rulesOrThrow(triage.defaultRules);
const urgencyRules = rulesOrThrow(triage.defaultUrgencyRule);

function response(department: Record<string, number>, confidence: number, score = 0.2): JevResponse {
  const choice = Object.entries(department).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "other";
  return {
    model: "m",
    answers: {
      department: { type: "choice", choice, confidence, probabilities: department },
      urgency: { type: "score", score, confidence: 0.9, probabilities: { "0": 0.8, "1": 0.1, "2": 0.1 } },
      return_reason: { type: "choice", choice: "damaged", confidence: 0.9, probabilities: { damaged: 0.95, other: 0.05 } },
      shipping_issue: { type: "choice", choice: "not_delivered", confidence: 0.8, probabilities: { not_delivered: 0.9, other: 0.1 } },
    },
    usage: { input_tokens: 1, output_tokens: 1 },
  };
}

const t = { minConfidence: 0.5, copyAbove: 0.25, urgentAt: 1.5 };

describe("route", () => {
  it("auto-routes a confident answer and reads only its branch question", () => {
    const r = route(response({ returns: 0.9, shipping: 0.05, billing: 0.05 }, 0.85), t);
    expect(r.path).toEqual({ kind: "auto", team: "returns", copies: [], issue: { question: "return_reason", label: "damaged", p: 0.95 } });
  });

  it("copies a second team whose probability is above the copy threshold", () => {
    const r = route(response({ billing: 0.6, shipping: 0.35, returns: 0.05 }, 0.6), t);
    expect(r.path).toEqual({ kind: "auto", team: "billing", copies: ["shipping"], issue: null });
  });

  it("sends a low-confidence answer to manual triage", () => {
    const r = route(response({ billing: 0.45, shipping: 0.4, returns: 0.15 }, 0.3), t);
    expect(r.path).toEqual({ kind: "manual", best: "billing" });
  });

  it("marks urgent at or above the urgency cut-off", () => {
    expect(route(response({ shipping: 0.9 }, 0.9, 1.6), t).urgent).toBe(true);
    expect(route(response({ shipping: 0.9 }, 0.9, 1.2), t).urgent).toBe(false);
  });
});

describe("triage regex", () => {
  it("routes by the first matching row of the table", () => {
    expect(triageRegex({ routing: rules, urgency: urgencyRules, text: "I was charged twice for a package that never came." })).toMatchObject({
      department: "shipping",
      urgent: false,
    });
  });

  it("treats shouting as urgent and an unmatched email as manual", () => {
    expect(triageRegex({ routing: rules, urgency: urgencyRules, text: "THIS IS RIDICULOUS!!! The new logo is hideous!!!" })).toMatchObject({
      department: "none",
      urgent: true,
    });
  });
});

describe("triage request", () => {
  it("asks department, urgency and both branch questions in one request", () => {
    const built = triage.build({ raw: { text: "hi" }, wording: triage.defaultWording, model: "m" });
    if (built.kind !== "ok") throw new Error(built.message);
    const q = built.request.questions;
    expect(Object.keys(q)).toEqual(["department", "urgency", "return_reason", "shipping_issue"]);
    expect(q.urgency?.type).toBe("score");
    if (q.urgency?.type === "score") expect(q.urgency.criteria).toHaveLength(3);
  });
});
