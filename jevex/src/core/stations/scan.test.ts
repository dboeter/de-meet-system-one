import { describe, expect, it } from "vitest";
import type { JevResponse } from "../jev.ts";
import { rulesOrThrow } from "../regex.ts";
import { readScan, scan, scanRegex, splitSentences } from "./scan.ts";

const MIXED = scan.presets[0]?.text ?? "";

describe("splitSentences", () => {
  it("splits on sentence punctuation and keeps exact offsets", () => {
    const text = "Thanks!  The charger is wrong. Could you send the right one?\nLove it";
    const spans = splitSentences(text);
    expect(spans.map((s) => s.text)).toEqual(["Thanks!", "The charger is wrong.", "Could you send the right one?", "Love it"]);
    for (const s of spans) expect(text.slice(s.start, s.end)).toBe(s.text);
  });

  it("splits the mixed ticket into six sentences", () => {
    expect(splitSentences(MIXED)).toHaveLength(6);
  });
});

describe("scan request", () => {
  it("asks one Noul per sentence, pointing at it by path in the state", () => {
    const built = scan.build({ raw: { text: "One. Two?" }, wording: scan.defaultWording, model: "m" });
    if (built.kind !== "ok") throw new Error(built.message);
    expect(built.request.state).toEqual({ email: "One. Two?", sentences: ["One.", "Two?"] });
    expect(Object.keys(built.request.questions)).toEqual(["s0", "s1"]);
    expect(built.request.questions.s1?.instructions).toContain("`sentences[1]`");
  });
});

describe("scan regex", () => {
  it("flags a sentence when a problem word appears, negated or not", () => {
    const rules = rulesOrThrow(scan.defaultRules);
    const hits = scanRegex(rules, splitSentences("This is not a problem. My code was rejected."));
    expect(hits.map((h) => h.hit !== null)).toEqual([true, false]);
  });
});

describe("readScan", () => {
  it("marks sentences at or above the threshold", () => {
    const sentences = splitSentences("Thanks. It broke.");
    const response: JevResponse = {
      model: "m",
      answers: { s0: { type: "noul", noul: 0.03 }, s1: { type: "noul", noul: 0.96 } },
      usage: { input_tokens: 1, output_tokens: 1 },
    };
    expect(readScan(response, sentences, 0.5).map((r) => [r.span.text, r.p, r.needsAction])).toEqual([
      ["Thanks.", 0.03, false],
      ["It broke.", 0.96, true],
    ]);
  });
});
