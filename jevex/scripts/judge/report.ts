/**
 * Score one or more judge run files against the Intent gold labels and write a markdown
 * report next to each run (`data/runs/<judge>.report.md`). Works for any judge whose run
 * file uses the `RunLine` shape, so a Haiku run is scored the same way.
 *
 * Usage: node scripts/judge/report.ts [data/runs/jev-1.13.0.jsonl ...]
 */
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { rulesOrThrow } from "../../src/core/regex.ts";
import { intent, intentRegexVerdict } from "../../src/core/stations/intent.ts";
import { parseIntentCases } from "./corpus.ts";
import { parseRunLines } from "./runs.ts";
import { CONFIDENCE_BUCKETS, summarize, type Ratio, type Summary } from "./stats.ts";

/** Same label but a moving probability is a different kind of instability than a label flip. */
const SPREAD_SHOWN = 0.1;

const pct =(r: Ratio): string => (r.n === 0 ? "–" : `${((100 * r.hit) / r.n).toFixed(1)}% (${r.hit}/${r.n})`);
const ms = (v: number | null): string => (v === null ? "–" : `${Math.round(v)} ms`);
const usd = (v: number | null, digits = 6): string => (v === null ? "–" : `$${v.toFixed(digits)}`);

function render(s: Summary, file: string): string {
  const wrong = s.cases.filter((c) => c.labels.some((l) => l !== c.gold));
  const unstable = s.cases.filter((c) => !c.unanimous);
  const drifting = s.cases.filter((c) => (c.goldProbSpread ?? 0) >= SPREAD_SHOWN);
  const bucketLabel = (from: number): string => {
    const next = CONFIDENCE_BUCKETS.find((b) => b > from);
    return next === undefined ? `≥ ${from}` : `${from} – ${next}`;
  };
  return [
    `# Intent judge report: ${s.judge}`,
    "",
    `Source: \`${file}\`, ${s.calls} calls over ${s.cases.length} cases. Gold labels: \`data/corpus.jsonl\`, rubric \`data/rubric.md\` (single annotator, not yet reviewed).`,
    "",
    "## Headline",
    "",
    "| Metric | Value |",
    "|---|---|",
    `| Accuracy, all calls | ${pct(s.accuracy)} |`,
    `| Accuracy, excluding \`ambiguous\` cases | ${pct(s.accuracyUnambiguous)} |`,
    `| Accuracy, easy (regex right) / hard (regex wrong) | ${pct(s.accuracyEasy)} / ${pct(s.accuracyHard)} |`,
    `| Majority-vote accuracy per case | ${pct(s.majority)} |`,
    `| Regex ladder on the same cases | ${pct(s.regexAccuracy)} |`,
    `| Cases with the same label on every repeat | ${pct(s.unanimous)} |`,
    `| Gold-label probability spread across repeats, mean / max | ${s.meanGoldProbSpread?.toFixed(3) ?? "–"} / ${s.maxGoldProbSpread?.toFixed(3) ?? "–"} |`,
    `| Latency warm p50 / p95 / max | ${ms(s.latencyWarm.p50)} / ${ms(s.latencyWarm.p95)} / ${ms(s.latencyWarm.max)} |`,
    `| Latency cold (first call) | ${s.latencyCold.map((v) => ms(v)).join(", ") || "–"} |`,
    `| Mean input tokens per call | ${s.meanInputTokens?.toFixed(1) ?? "–"} |`,
    `| Cost per call (mean) / whole run | ${usd(s.meanCostUsd, 7)} / ${usd(s.totalCostUsd)} |`,
    `| Cost per 1,000 emails | ${usd(s.meanCostUsd === null ? null : s.meanCostUsd * 1000, 4)} |`,
    `| Failed calls (no retries) | ${s.errors} of ${s.calls} |`,
    "",
    "Latency is client wall clock for one HTTPS round trip from this machine, calls in series.",
    "",
    "## Accuracy per repeat",
    "",
    "| Repeat | Accuracy |",
    "|---|---|",
    ...s.perRepeat.map((r) => `| ${r.repeat} | ${pct(r.accuracy)} |`),
    "",
    "## Accuracy per gold label",
    "",
    "| Gold | Accuracy |",
    "|---|---|",
    ...s.perLabel.map((l) => `| ${l.label} | ${pct(l.accuracy)} |`),
    "",
    "## Accuracy by reported confidence",
    "",
    "| Confidence | Accuracy |",
    "|---|---|",
    ...s.calibration.map((b) => `| ${bucketLabel(b.from)} | ${pct(b.accuracy)} |`),
    "",
    "## Cases answered wrong at least once",
    "",
    wrong.length === 0 ? "None." : "| Case | Gold | Labels per repeat | Mean p(gold) | Tags |",
    ...(wrong.length === 0 ? [] : ["|---|---|---|---|---|"]),
    ...wrong.map((c) => `| ${c.id} | ${c.gold} | ${c.labels.join(", ")} | ${c.meanGoldProb?.toFixed(2) ?? "–"} | ${c.tags.join(", ")} |`),
    "",
    "## Cases whose label changed between repeats",
    "",
    unstable.length === 0 ? "None." : unstable.map((c) => `- ${c.id}: ${c.labels.join(", ")} (gold ${c.gold})`).join("\n"),
    "",
    `## Cases whose p(gold) moved by ${SPREAD_SHOWN} or more between repeats`,
    "",
    drifting.length === 0
      ? "None."
      : drifting.map((c) => `- ${c.id}: spread ${c.goldProbSpread?.toFixed(2)}, mean p(gold) ${c.meanGoldProb?.toFixed(2)}, labels ${c.labels.join(", ")}`).join("\n"),
    "",
  ].join("\n");
}

const files = process.argv.slice(2).length > 0
  ? process.argv.slice(2)
  : readdirSync("data/runs").filter((f) => f.endsWith(".jsonl")).map((f) => `data/runs/${f}`);
const cases = parseIntentCases(readFileSync("data/corpus.jsonl", "utf8"));
const rules = rulesOrThrow(intent.defaultRules);

for (const file of files) {
  const summary = summarize({
    cases,
    lines: parseRunLines(readFileSync(file, "utf8")),
    regex: (text) => intentRegexVerdict(rules, text).label,
  });
  const out = file.replace(/\.jsonl$/, ".report.md");
  writeFileSync(out, render(summary, file));
  process.stdout.write(`${summary.judge}: accuracy ${pct(summary.accuracy)}, unanimous ${pct(summary.unanimous)}, ` +
    `p50 ${ms(summary.latencyWarm.p50)}, p95 ${ms(summary.latencyWarm.p95)}, ${usd(summary.meanCostUsd, 7)}/call → ${out}\n`);
}
