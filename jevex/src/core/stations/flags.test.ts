import { describe, expect, it } from "vitest";
import type { JevResponse } from "../jev.ts";
import { rulesOrThrow } from "../regex.ts";
import { FLAGS, flags, flagsRegex, readFlags } from "./flags.ts";

const rules = rulesOrThrow(flags.defaultRules);

describe("flags regex", () => {
  it("tests every flag's pattern independently", () => {
    const hits = flagsRegex(rules, "I'm not a lawyer, but please refund me or I'll file a chargeback.");
    expect(Object.keys(hits)).toEqual([...FLAGS]);
    expect(hits.asks_refund_now?.text).toBe("refund");
    expect(hits.legal_or_chargeback_threat?.text).toBe("lawyer");
    expect(hits.wants_human).toBeNull();
  });

  it("fires on 'manager' for a customer who does not want a human", () => {
    expect(flagsRegex(rules, "My manager asked me to order 40 more of these.").wants_human?.text).toBe("manager");
  });

  it("misses a repeat contact phrased without its keywords", () => {
    expect(flagsRegex(rules, "Third time writing about this and still nothing.").repeat_contact).toBeNull();
  });
});

describe("flags request", () => {
  it("asks one Noul per flag over the email", () => {
    const built = flags.build({ raw: { text: "hi" }, wording: flags.defaultWording, model: "m" });
    if (built.kind !== "ok") throw new Error(built.message);
    expect(Object.keys(built.request.questions)).toEqual([...FLAGS]);
    expect(Object.values(built.request.questions).every((q) => q.type === "noul")).toBe(true);
  });
});

describe("readFlags", () => {
  it("bands every flag with its own thresholds", () => {
    const response: JevResponse = {
      model: "m",
      answers: {
        asks_refund_now: { type: "noul", noul: 0.95 },
        wants_human: { type: "noul", noul: 0.4 },
        repeat_contact: { type: "noul", noul: 0.05 },
        legal_or_chargeback_threat: { type: "noul", noul: 0.3 },
        cancellation_risk: { type: "noul", noul: 0.1 },
      },
      usage: { input_tokens: 1, output_tokens: 1 },
    };
    const t = { no: 0.2, yes: 0.8 };
    const read = readFlags(response, { ...flags.defaultThresholds, legal_or_chargeback_threat: { no: 0.35, yes: 0.8 } });
    expect(read.map((r) => [r.flag, r.band])).toEqual([
      ["asks_refund_now", "yes"],
      ["wants_human", "review"],
      ["repeat_contact", "no"],
      ["legal_or_chargeback_threat", "no"],
      ["cancellation_risk", "no"],
    ]);
    expect(flags.defaultThresholds.wants_human).toEqual(t);
  });
});
