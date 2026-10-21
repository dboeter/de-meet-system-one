import { describe, expect, it } from "vitest";
import { againstNoise, parseCorpus, repeatNoise, scoreCorpus, TASK_NOISE, type CorpusItem, type TaskScore } from "./eval.ts";
import type { JevResponse } from "./jev.ts";
import { rulesOrThrow } from "./regex.ts";
import { flags } from "./stations/flags.ts";
import { intent } from "./stations/intent.ts";
import { triage } from "./stations/triage.ts";

const usage = { input_tokens: 1, output_tokens: 1 };
const choice = (c: string, p = 0.9) => ({ type: "choice" as const, choice: c, confidence: p, probabilities: { [c]: p } });

const corpus = [
  { station: "intent", id: "i1", text: "Please refund my order.", gold: "refund", tags: ["easy"], note: "" },
  { station: "intent", id: "i2", text: "The refund came through, thanks!", gold: "praise", tags: ["hard"], note: "" },
  { station: "intent", id: "i3", text: "pls refnd", gold: "refund", tags: ["hard", "ambiguous"], note: "" },
  {
    station: "flags",
    id: "f1",
    text: "My manager asked me to order more.",
    gold: { asks_refund_now: false, wants_human: false, repeat_contact: false, legal_or_chargeback_threat: false, cancellation_risk: false },
    tags: [],
    note: "",
  },
  { station: "triage", id: "t1", text: "The wedding is Saturday and the dress is not here.", gold: { department: "shipping", urgent: true }, tags: [], note: "" },
]
  .map((x) => JSON.stringify(x))
  .join("\n");

const responses = new Map<string, JevResponse>([
  ["i1", { model: "m", answers: { intent: choice("refund") }, usage }],
  ["i2", { model: "m", answers: { intent: choice("refund") }, usage }],
  ["i3", { model: "m", answers: { intent: choice("refund") }, usage }],
  [
    "f1",
    {
      model: "m",
      answers: {
        asks_refund_now: { type: "noul", noul: 0.02 },
        wants_human: { type: "noul", noul: 0.1 },
        repeat_contact: { type: "noul", noul: 0.02 },
        legal_or_chargeback_threat: { type: "noul", noul: 0.01 },
        cancellation_risk: { type: "noul", noul: 0.6 },
      },
      usage,
    },
  ],
  [
    "t1",
    {
      model: "m",
      answers: {
        department: choice("shipping"),
        urgency: { type: "score", score: 1.8, confidence: 0.8, probabilities: { "0": 0.05, "1": 0.1, "2": 0.85 } },
      },
      usage,
    },
  ],
]);

const rules = {
  intent: rulesOrThrow(intent.defaultRules),
  flags: rulesOrThrow(flags.defaultRules),
  triage: rulesOrThrow(triage.defaultRules),
  urgency: rulesOrThrow(triage.defaultUrgencyRule),
};

describe("parseCorpus", () => {
  it("parses every station's gold shape", () => {
    const items = parseCorpus(corpus);
    expect(items.map((i: CorpusItem) => i.station)).toEqual(["intent", "intent", "intent", "flags", "triage"]);
  });

  it("rejects a line whose gold does not fit its station", () => {
    expect(() => parseCorpus(JSON.stringify({ station: "intent", id: "x", text: "t", gold: "nope", tags: [], note: "" }))).toThrow(/line 1/);
  });
});

describe("scoreCorpus", () => {
  const score = scoreCorpus({ items: parseCorpus(corpus), rules, responses });

  it("scores intent, excluding ambiguous cases from accuracy", () => {
    expect(score.tasks.find((t) => t.task === "intent")).toEqual({
      task: "intent",
      total: 2,
      excluded: 1,
      regexCorrect: 1,
      jevCorrect: 1,
      jevMissing: 0,
      jevReview: 0,
    });
  });

  it("scores flags per flag decision with the screen's review band", () => {
    // Regex fires on "manager" (wrong); Jev's cancellation_risk 0.6 sits in the 0.2–0.8 review band.
    expect(score.tasks.find((t) => t.task === "flags")).toMatchObject({ total: 5, regexCorrect: 4, jevCorrect: 4, jevReview: 1 });
  });

  it("scores triage department and urgency separately", () => {
    expect(score.tasks.find((t) => t.task === "triage-department")).toMatchObject({ total: 1, regexCorrect: 0, jevCorrect: 1 });
    expect(score.tasks.find((t) => t.task === "triage-urgency")).toMatchObject({ total: 1, regexCorrect: 0, jevCorrect: 1 });
  });

  it("lists only the decisions where regex and Jev disagree", () => {
    // i1 and i2: regex and Jev agree (right and both wrong), so they are not listed.
    expect(score.disagreements.map((d) => [d.id, d.task, d.gold, d.regex, d.jev])).toEqual([
      ["f1", "flags:wants_human", "no", "yes", "no"],
      ["f1", "flags:cancellation_risk", "no", "no", "review"],
      ["t1", "triage-department", "shipping", "other", "shipping"],
      ["t1", "triage-urgency", "urgent", "not urgent", "urgent"],
    ]);
  });

  it("counts a case without a recording as missing for Jev", () => {
    const partial = scoreCorpus({ items: parseCorpus(corpus), rules, responses: new Map() });
    expect(partial.tasks.find((t) => t.task === "intent")).toMatchObject({ jevCorrect: 0, jevMissing: 2 });
  });
});

describe("repeatNoise", () => {
  const choiceAnswer = (choice: string, p: number) => ({ type: "choice" as const, choice, confidence: p, probabilities: { [choice]: p, other: 1 - p } });
  const triageResponse = (department: string, score: number, issue: string): JevResponse => ({
    model: "m",
    answers: {
      department: choiceAnswer(department, 0.9),
      urgency: { type: "score", score, confidence: 0.8, probabilities: { "0": 0.1, "1": 0.5, "2": 0.4 } },
      shipping_issue: choiceAnswer(issue, 0.6),
    },
    usage,
  });

  it("counts a case as flipped only when the task's own decision changes", () => {
    // Case 1: only the unused branch question changes. Case 2: urgency crosses the 1.5 cut-off.
    const groups = [
      [triageResponse("billing", 1.0, "delayed"), triageResponse("billing", 1.0, "not_delivered")],
      [triageResponse("billing", 1.49, "other"), triageResponse("billing", 1.54, "other")],
    ];
    expect(repeatNoise(groups, TASK_NOISE["triage-department"])).toMatchObject({ items: 2, flipped: 0 });
    expect(repeatNoise(groups, TASK_NOISE["triage-urgency"])).toMatchObject({ items: 2, flipped: 1 });
  });

  it("reports the largest probability move within the task's questions", () => {
    const a: JevResponse = { model: "m", answers: { intent: { type: "choice", choice: "exchange", confidence: 0.85, probabilities: { exchange: 0.9, refund: 0.1 } } }, usage };
    const b: JevResponse = { model: "m", answers: { intent: { type: "choice", choice: "exchange", confidence: 0.48, probabilities: { exchange: 0.6, refund: 0.4 } } }, usage };
    expect(repeatNoise([[a, b]], TASK_NOISE.intent)).toEqual({ items: 1, flipped: 0, maxDelta: expect.closeTo(0.3) });
  });
});

describe("againstNoise", () => {
  const task: TaskScore = { task: "intent", total: 47, excluded: 2, regexCorrect: 19, jevCorrect: 45, jevMissing: 0, jevReview: 0 };

  it("bounds the noise from the pilot even when no repeat flipped", () => {
    // 0 of 10 flipped: the 95% Wilson upper bound is 0.278, so up to 14 of 47 decisions.
    expect(againstNoise(task, { items: 10, flipped: 0, maxDelta: 0.04 })).toEqual({ kind: "compared", gap: 26, noise: 14, beyondNoise: true });
  });

  it("calls a gap within the noise bound not beyond it", () => {
    expect(againstNoise({ ...task, regexCorrect: 40 }, { items: 10, flipped: 2, maxDelta: 0.3 })).toMatchObject({ gap: 5, beyondNoise: false });
  });

  it("says when there is no pilot to compare against", () => {
    expect(againstNoise(task, { items: 0, flipped: 0, maxDelta: 0 })).toEqual({ kind: "no_pilot" });
  });
});
