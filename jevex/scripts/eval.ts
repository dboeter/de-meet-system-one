/**
 * Score the regex baselines and recorded Jev answers over data/corpus.jsonl.
 * Prints a table and writes eval/results.json. Needs no network and no key.
 * Usage: npm run eval
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { MODEL } from "../src/core/config.ts";
import { againstNoise, corpusResponses, corpusTaskNoise, parseCorpus, scoreCorpus } from "../src/core/eval.ts";
import { parseRecordings, RecordingStore } from "../src/core/recording.ts";
import { rulesOrThrow } from "../src/core/regex.ts";
import { flags } from "../src/core/stations/flags.ts";
import { intent } from "../src/core/stations/intent.ts";
import { triage } from "../src/core/stations/triage.ts";

const CORPUS = "data/corpus.jsonl";
if (!existsSync(CORPUS)) {
  process.stderr.write(`${CORPUS} not found\n`);
  process.exit(1);
}

const items = parseCorpus(readFileSync(CORPUS, "utf8"));
const store = new RecordingStore(parseRecordings(readFileSync("src/recordings/recordings.jsonl", "utf8")));
const rules = {
  intent: rulesOrThrow(intent.defaultRules),
  flags: rulesOrThrow(flags.defaultRules),
  triage: rulesOrThrow(triage.defaultRules),
  urgency: rulesOrThrow(triage.defaultUrgencyRule),
};
const score = scoreCorpus({ items, rules, responses: await corpusResponses(items, store, MODEL) });
const noise = await corpusTaskNoise(items, store, MODEL);
const comparisons = score.tasks.map((t) => ({ task: t.task, ...againstNoise(t, noise[t.task]) }));

const pct = (n: number, d: number) => (d === 0 ? "  n/a" : `${((100 * n) / d).toFixed(0).padStart(4)}%`);
const lines = [
  `Model ${MODEL}, ${items.length} labelled cases`,
  "",
  "task                 decisions  regex   jev   missing  review  excluded  gap vs noise",
  ...score.tasks.map((t, i) => {
    const c = comparisons[i];
    const gap = !c || c.kind === "no_pilot" ? "n/a" : `${c.gap > 0 ? "+" : ""}${c.gap} vs ≤${c.noise}${c.beyondNoise ? "" : " (within noise)"}`;
    return `${t.task.padEnd(20)} ${String(t.total).padStart(9)}  ${pct(t.regexCorrect, t.total)} ${pct(t.jevCorrect, t.total)}  ${String(t.jevMissing).padStart(7)}  ${String(t.jevReview).padStart(6)}  ${String(t.excluded).padStart(8)}  ${gap}`;
  }),
  "",
  ...Object.entries(noise)
    .filter(([, n]) => n.items > 0)
    .map(([t, n]) => `Repeat noise (${t}): ${n.flipped} of ${n.items} repeated cases changed this decision; largest probability move ${n.maxDelta.toFixed(2)}`),
  "Noise ≤N: the 95% upper bound on how many decisions repeat noise could move.",
  `Disagreements (regex ≠ Jev): ${score.disagreements.length}`,
];
process.stdout.write(`${lines.join("\n")}\n`);

mkdirSync("eval", { recursive: true });
writeFileSync(
  "eval/results.json",
  `${JSON.stringify({ model: MODEL, cases: items.length, tasks: score.tasks, repeatNoise: noise, againstNoise: comparisons, disagreements: score.disagreements }, null, 2)}\n`,
);
