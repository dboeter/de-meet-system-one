import type { IntentCase } from "./corpus.ts";
import type { RunLine } from "./runs.ts";

/** The regex ladder says `none` when nothing matches; the rubric scores that as `other`. */
export function regexLabel(label: string): string {
  return label === "none" ? "other" : label;
}

/** Nearest-rank percentile of a non-empty list, `null` for an empty one. */
export function percentile(values: readonly number[], p: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = Math.max(1, Math.ceil((p / 100) * sorted.length));
  return sorted[rank - 1] ?? null;
}

const mean = (xs: readonly number[]): number | null => (xs.length === 0 ? null : xs.reduce((a, b) => a + b, 0) / xs.length);

export type Ratio = { readonly hit: number; readonly n: number };
const ratio = (flags: readonly boolean[]): Ratio => ({ hit: flags.filter(Boolean).length, n: flags.length });

/** Confidence buckets for the calibration table, lower bound inclusive. */
export const CONFIDENCE_BUCKETS = [0, 0.5, 0.8, 0.95] as const;

export type CaseSummary = {
  readonly id: string;
  readonly gold: string;
  readonly tags: readonly string[];
  /** Answer label per repeat, in repeat order. */
  readonly labels: readonly string[];
  readonly unanimous: boolean;
  /** Max minus min of the probability given to the gold label across repeats. */
  readonly goldProbSpread: number | null;
  readonly meanGoldProb: number | null;
};

export type Summary = {
  readonly judge: string;
  readonly calls: number;
  readonly errors: number;
  readonly accuracy: Ratio;
  readonly accuracyUnambiguous: Ratio;
  readonly accuracyEasy: Ratio;
  readonly accuracyHard: Ratio;
  readonly perRepeat: readonly { readonly repeat: number; readonly accuracy: Ratio }[];
  readonly majority: Ratio;
  readonly unanimous: Ratio;
  readonly maxGoldProbSpread: number | null;
  readonly meanGoldProbSpread: number | null;
  readonly perLabel: readonly { readonly label: string; readonly accuracy: Ratio }[];
  readonly calibration: readonly { readonly from: number; readonly accuracy: Ratio }[];
  readonly latencyWarm: { readonly p50: number | null; readonly p95: number | null; readonly max: number | null; readonly mean: number | null };
  readonly latencyCold: readonly number[];
  readonly meanInputTokens: number | null;
  readonly totalCostUsd: number | null;
  readonly meanCostUsd: number | null;
  readonly cases: readonly CaseSummary[];
  readonly regexAccuracy: Ratio;
};

export function summarize(args: {
  readonly cases: readonly IntentCase[];
  readonly lines: readonly RunLine[];
  readonly regex: (text: string) => string;
}): Summary {
  const { cases, lines, regex } = args;
  const byId = new Map(cases.map((c) => [c.id, c]));
  const answered = lines.flatMap((l) => {
    const c = byId.get(l.case_id);
    return l.outcome.kind === "answer" && c ? [{ line: l, case: c, label: l.outcome.label, outcome: l.outcome }] : [];
  });
  const correct = (a: (typeof answered)[number]): boolean => a.label === a.case.gold;
  const where = (pred: (a: (typeof answered)[number]) => boolean): Ratio => ratio(answered.filter(pred).map(correct));

  const repeats = [...new Set(answered.map((a) => a.line.repeat))].sort((a, b) => a - b);
  const caseSummaries: CaseSummary[] = cases.map((c) => {
    const mine = answered.filter((a) => a.case.id === c.id).sort((a, b) => a.line.repeat - b.line.repeat);
    const goldProbs = mine.flatMap((a) => (a.outcome.probabilities ? [a.outcome.probabilities[c.gold] ?? 0] : []));
    const labels = mine.map((a) => a.label);
    return {
      id: c.id,
      gold: c.gold,
      tags: c.tags,
      labels,
      unanimous: labels.length > 0 && labels.every((l) => l === labels[0]),
      goldProbSpread: goldProbs.length > 1 ? Math.max(...goldProbs) - Math.min(...goldProbs) : null,
      meanGoldProb: mean(goldProbs),
    };
  });
  const answeredCases = caseSummaries.filter((c) => c.labels.length > 0);
  const modal = (labels: readonly string[]): string | undefined => {
    const counts = new Map<string, number>();
    for (const l of labels) counts.set(l, (counts.get(l) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  };
  const spreads = answeredCases.flatMap((c) => (c.goldProbSpread === null ? [] : [c.goldProbSpread]));

  const warm = answered.filter((a) => !a.line.cold).map((a) => a.line.latency_ms);
  const costs = lines.flatMap((l) => (l.cost_usd === null ? [] : [l.cost_usd]));
  const tokens = lines.flatMap((l) => (l.input_tokens === null ? [] : [l.input_tokens]));
  const bucketOf = (conf: number): number => CONFIDENCE_BUCKETS.filter((b) => conf >= b).at(-1) ?? 0;

  return {
    judge: lines[0]?.judge ?? "unknown",
    calls: lines.length,
    errors: lines.filter((l) => l.outcome.kind === "error").length,
    accuracy: where(() => true),
    accuracyUnambiguous: where((a) => !a.case.tags.includes("ambiguous")),
    accuracyEasy: where((a) => a.case.tags.includes("easy")),
    accuracyHard: where((a) => a.case.tags.includes("hard")),
    perRepeat: repeats.map((repeat) => ({ repeat, accuracy: where((a) => a.line.repeat === repeat) })),
    majority: ratio(answeredCases.map((c) => modal(c.labels) === c.gold)),
    unanimous: ratio(answeredCases.map((c) => c.unanimous)),
    maxGoldProbSpread: spreads.length === 0 ? null : Math.max(...spreads),
    meanGoldProbSpread: mean(spreads),
    perLabel: [...new Set(cases.map((c) => c.gold))].map((label) => ({ label, accuracy: where((a) => a.case.gold === label) })),
    calibration: CONFIDENCE_BUCKETS.map((from) => ({
      from,
      accuracy: where((a) => a.outcome.confidence !== null && bucketOf(a.outcome.confidence) === from),
    })),
    latencyWarm: { p50: percentile(warm, 50), p95: percentile(warm, 95), max: percentile(warm, 100), mean: mean(warm) },
    latencyCold: answered.filter((a) => a.line.cold).map((a) => a.line.latency_ms),
    meanInputTokens: mean(tokens),
    totalCostUsd: costs.length === 0 ? null : costs.reduce((a, b) => a + b, 0),
    meanCostUsd: mean(costs),
    cases: caseSummaries,
    regexAccuracy: ratio(cases.map((c) => regexLabel(regex(c.text)) === c.gold)),
  };
}
