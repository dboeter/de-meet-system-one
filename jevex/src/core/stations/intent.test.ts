import { describe, expect, it } from "vitest";
import { MAX_INPUT_CHARS } from "../config.ts";
import type { JevResponse } from "../jev.ts";
import { intent, intentRegexVerdict, readIntent } from "./intent.ts";
import { rulesOrThrow } from "../regex.ts";

describe("intent regex ladder", () => {
  // Expected values are the "Regex says" column of the preset table in docs/spec.md.
  const table: [string, string][] = [
    ["The refund came through yesterday, thanks!", "refund"],
    ["Give me back what I paid, this thing is useless.", "complaint"],
    ["I don't want a refund, just send one that works.", "refund"],
    ["Great, thanks for shipping it to the wrong city.", "praise"],
    ["Can I get my money back if it's still sealed?", "refund"],
    ["Please don't cancel my subscription, I only wanted to know when it renews.", "cancel"],
    ["pls refnd order 4471", "none"],
  ];
  const rules = rulesOrThrow(intent.defaultRules);

  it.each(table)("%s → %s", (text, expected) => {
    expect(intentRegexVerdict(rules, text).label).toBe(expected);
  });

  it("every preset's recorded regex verdict is wrong against its gold label", () => {
    for (const preset of intent.presets) {
      expect(intentRegexVerdict(rules, preset.text).label).not.toBe(preset.gold);
    }
  });
});

describe("intent request", () => {
  it("asks one Choice over the seven intents with the email as state", () => {
    const built = intent.build({ raw: { text: "hi" }, wording: intent.defaultWording, model: "m" });
    if (built.kind !== "ok") throw new Error(built.message);
    expect(built.request.state).toBe("hi");
    const q = built.request.questions.intent;
    expect(q?.type).toBe("choice");
    if (q?.type !== "choice") return;
    expect(Object.keys(q.criteria)).toEqual(["refund", "exchange", "cancel", "complaint", "question", "praise", "other"]);
  });

  it("rejects empty and over-long text", () => {
    expect(intent.build({ raw: { text: " " }, wording: intent.defaultWording, model: "m" }).kind).toBe("error");
    const long = intent.build({ raw: { text: "x".repeat(MAX_INPUT_CHARS + 1) }, wording: intent.defaultWording, model: "m" });
    expect(long).toMatchObject({ kind: "error", reason: "too_long" });
  });
});

describe("readIntent", () => {
  it("returns the choice, its confidence and options ranked by probability", () => {
    const response: JevResponse = {
      model: "jev-1.13.0",
      answers: {
        intent: { type: "choice", choice: "praise", confidence: 0.92, probabilities: { refund: 0.03, praise: 0.95, other: 0.02 } },
      },
      usage: { input_tokens: 1, output_tokens: 1 },
    };
    expect(readIntent(response)).toEqual({
      label: "praise",
      confidence: 0.92,
      ranked: [
        { label: "praise", p: 0.95 },
        { label: "refund", p: 0.03 },
        { label: "other", p: 0.02 },
      ],
    });
  });
});
