import { describe, expect, it } from "vitest";
import type { JevResponse } from "../jev.ts";
import { extract, findCandidates, NONE, readPick } from "./extract.ts";

const ORDER_EMAIL =
  "Orders A-1182 and A-1190 arrived. A-1182 is fine, but the lamp in A-1190 is cracked and I want my money back for it.";

function pickResponse(choice: string, probabilities: Record<string, number>): JevResponse {
  return { model: "m", answers: { pick: { type: "choice", choice, confidence: 0.9, probabilities } }, usage: { input_tokens: 1, output_tokens: 1 } };
}

describe("findCandidates", () => {
  it("returns every match span and the distinct values in order of first appearance", () => {
    const found = findCandidates(extract.finders.order, ORDER_EMAIL);
    expect(found.spans.map((s) => s.text)).toEqual(["A-1182", "A-1190", "A-1182", "A-1190"]);
    expect(found.candidates).toEqual(["A-1182", "A-1190"]);
  });

  it("finds every money amount on an invoice", () => {
    const invoice = extract.presets.find((p) => p.kind === "amount");
    if (!invoice) throw new Error("no amount preset");
    expect(findCandidates(extract.finders.amount, invoice.text).candidates).toContain(invoice.gold);
  });
});

describe("extract request", () => {
  it("offers the candidates plus none as the Choice options", () => {
    const built = extract.build({ raw: { kind: "order", text: ORDER_EMAIL, candidates: ["A-1182", "A-1190"] }, wording: extract.defaultWording, model: "m" });
    if (built.kind !== "ok") throw new Error(built.message);
    const q = built.request.questions.pick;
    if (q?.type !== "choice") throw new Error("expected a choice");
    expect(Object.keys(q.criteria)).toEqual(["A-1182", "A-1190", NONE]);
  });

  it("rejects a candidate that is not in the text", () => {
    const built = extract.build({ raw: { kind: "order", text: ORDER_EMAIL, candidates: ["A-9999"] }, wording: extract.defaultWording, model: "m" });
    expect(built.kind).toBe("error");
  });

  it("rejects an empty candidate list, so zero candidates never reach Jev", () => {
    const built = extract.build({ raw: { kind: "order", text: ORDER_EMAIL, candidates: [] }, wording: extract.defaultWording, model: "m" });
    expect(built.kind).toBe("error");
  });
});

describe("readPick", () => {
  const candidates = ["A-1182", "A-1190"];

  it("returns the picked candidate, copied verbatim, with its probability", () => {
    expect(readPick(pickResponse("A-1190", { "A-1182": 0.03, "A-1190": 0.96, none: 0.01 }), candidates)).toEqual({ kind: "picked", value: "A-1190", p: 0.96 });
  });

  it("returns none when Jev picks none", () => {
    expect(readPick(pickResponse(NONE, { "A-1182": 0.1, "A-1190": 0.1, none: 0.8 }), candidates)).toEqual({ kind: "none", p: 0.8 });
  });

  it("refuses an answer that is not one of the candidates", () => {
    expect(() => readPick(pickResponse("A-2000", { "A-2000": 1 }), candidates)).toThrow(/not one of the candidates/);
  });
});
