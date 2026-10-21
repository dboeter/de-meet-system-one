import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { rulesOrThrow } from "../../src/core/regex.ts";
import { parseCorpus } from "../../src/core/eval.ts";
import { FLAGS, flags, flagsRegex } from "../../src/core/stations/flags.ts";
import { intent, intentRegexVerdict } from "../../src/core/stations/intent.ts";
import { DEPARTMENTS, triage, triageRegex } from "../../src/core/stations/triage.ts";
import { parseIntentCases } from "./corpus.ts";
import { regexLabel } from "./stats.ts";

const cases = parseIntentCases(readFileSync("data/corpus.jsonl", "utf8"));
const rules = rulesOrThrow(intent.defaultRules);

describe("intent corpus", () => {
  it("has 25–60 cases covering every label", () => {
    expect(cases.length).toBeGreaterThanOrEqual(25);
    expect(cases.length).toBeLessThanOrEqual(60);
    for (const label of ["refund", "exchange", "cancel", "complaint", "question", "praise", "other"]) {
      expect(cases.some((c) => c.gold === label), label).toBe(true);
    }
  });

  it("tags every case exactly one of easy or hard", () => {
    for (const c of cases) expect(c.tags.includes("easy") !== c.tags.includes("hard"), c.id).toBe(true);
  });

  // The rubric defines `easy` as "the regex ladder gets it right", so the tag is checked, not trusted.
  it.each(cases.map((c) => [c.id, c] as const))("%s: easy/hard tag matches the regex ladder", (_id, c) => {
    const regexRight = regexLabel(intentRegexVerdict(rules, c.text).label) === c.gold;
    expect(regexRight).toBe(c.tags.includes("easy"));
  });

  it("contains every Intent preset with the same gold label", () => {
    for (const p of intent.presets) {
      expect(cases.find((c) => c.text === p.text)?.gold, p.id).toBe(p.gold);
    }
  });
});

describe("flags and triage corpus", () => {
  const items = parseCorpus(readFileSync("data/corpus.jsonl", "utf8"));
  const flagItems = items.flatMap((i) => (i.station === "flags" ? [i] : []));
  const triageItems = items.flatMap((i) => (i.station === "triage" ? [i] : []));
  const flagRules = rulesOrThrow(flags.defaultRules);
  const routing = rulesOrThrow(triage.defaultRules);
  const urgency = rulesOrThrow(triage.defaultUrgencyRule);

  it("has 25–40 cases per station and unique ids across the corpus", () => {
    expect(flagItems.length).toBeGreaterThanOrEqual(25);
    expect(flagItems.length).toBeLessThanOrEqual(40);
    expect(triageItems.length).toBeGreaterThanOrEqual(25);
    expect(triageItems.length).toBeLessThanOrEqual(40);
    expect(new Set(items.map((i) => i.id)).size).toBe(items.length);
  });

  it("makes every flag true at least twice and every department gold at least twice", () => {
    for (const f of FLAGS) expect(flagItems.filter((i) => i.gold[f]).length, f).toBeGreaterThanOrEqual(2);
    for (const d of DEPARTMENTS) expect(triageItems.filter((i) => i.gold.department === d).length, d).toBeGreaterThanOrEqual(2);
    expect(triageItems.some((i) => i.gold.urgent)).toBe(true);
  });

  // `easy` means the regex is right on every part of the gold label (rubric, Flags and Triage tags).
  it.each(flagItems.map((i) => [i.id, i] as const))("%s: easy/hard tag matches the flag regexes", (_id, i) => {
    const verdict = flagsRegex(flagRules, i.text);
    const regexRight = FLAGS.every((f) => (verdict[f] !== null) === i.gold[f]);
    expect(i.tags.includes("easy") !== i.tags.includes("hard")).toBe(true);
    expect(regexRight).toBe(i.tags.includes("easy"));
  });

  it.each(triageItems.map((i) => [i.id, i] as const))("%s: easy/hard tag matches the routing regex", (_id, i) => {
    const verdict = triageRegex({ routing, urgency, text: i.text });
    const regexRight = regexLabel(verdict.department) === i.gold.department && verdict.urgent === i.gold.urgent;
    expect(i.tags.includes("easy") !== i.tags.includes("hard")).toBe(true);
    expect(regexRight).toBe(i.tags.includes("easy"));
  });

  it("contains every Flags and Triage preset with the same gold label", () => {
    for (const p of flags.presets) expect(flagItems.find((i) => i.text === p.text)?.gold, p.id).toEqual(p.gold);
    for (const p of triage.presets) expect(triageItems.find((i) => i.text === p.text)?.gold, p.id).toEqual(p.gold);
  });
});
