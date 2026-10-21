/**
 * Ask Jev the Intent station's question for every corpus case, several times, and append one
 * line per call to `data/runs/<model>.jsonl`. Pairs (case, repeat) already in the file are
 * skipped, so a re-run only fills gaps and failed calls.
 *
 * Usage: node scripts/judge/run-jev.ts [--repeats N] [--dry-run]
 *
 * Calls run one at a time with SDK retries off, so `latency_ms` is one attempt and failures
 * show up as error lines instead of hidden retries. Repeats run as whole passes over the
 * corpus, so two calls with the same request are never back to back.
 * Writes only under data/runs/; the demo's recordings are not touched.
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { APIConnectionError, APIError, TypeSafeClient, type SystemOneRequest } from "@typesafe-ai/sdk";
import { costUsd, MODEL } from "../../src/core/config.ts";
import { parseJevResponse } from "../../src/core/jev.ts";
import { intent, readIntent } from "../../src/core/stations/intent.ts";
import { parseIntentCases } from "./corpus.ts";
import { parseRunLines, type Outcome, type RunLine } from "./runs.ts";

const CORPUS = "data/corpus.jsonl";
const OUT = `data/runs/${MODEL}.jsonl`;

function flag(name: string): string | undefined {
  const i = process.argv.indexOf(name);
  return i === -1 ? undefined : process.argv[i + 1];
}
const repeats = Number(flag("--repeats") ?? 5);
if (!Number.isInteger(repeats) || repeats < 1) throw new Error("--repeats must be a positive integer");
const dryRun = process.argv.includes("--dry-run");

const cases = parseIntentCases(readFileSync(CORPUS, "utf8"));
// Error lines do not count as done, so failed calls are retried on the next run.
const done = new Set(
  (existsSync(OUT) ? parseRunLines(readFileSync(OUT, "utf8")) : [])
    .filter((l) => l.outcome.kind === "answer")
    .map((l) => `${l.case_id}#${l.repeat}`),
);

const jobs = Array.from({ length: repeats }, (_, repeat) => cases.map((c) => ({ c, repeat })))
  .flat()
  .filter(({ c, repeat }) => !done.has(`${c.id}#${repeat}`));
process.stdout.write(`${jobs.length} call(s) to make for ${MODEL} (${cases.length} cases × ${repeats} repeats)\n`);
if (dryRun || jobs.length === 0) process.exit(0);

if (existsSync(".env")) process.loadEnvFile();
const client = new TypeSafeClient({ retry: { maxRetries: 0 }, timeout: 30_000 });
mkdirSync("data/runs", { recursive: true });

let failed = 0;
for (const [n, { c, repeat }] of jobs.entries()) {
  const built = intent.build({ raw: { text: c.text }, wording: intent.defaultWording, model: MODEL });
  if (built.kind === "error") throw new Error(`${c.id}: ${built.message}`);
  const startedAt = new Date().toISOString();
  const started = performance.now();
  let outcome: Outcome;
  let raw: unknown = null;
  let usage: { input_tokens: number | null; output_tokens: number | null } = { input_tokens: null, output_tokens: null };
  let judge = MODEL;
  try {
    // Our request type is the readonly JSON subset of the SDK's; the SDK's types are mutable.
    raw = await client.systemOne(built.request as SystemOneRequest);
    const response = parseJevResponse(raw);
    if (!response) throw new Error("unreadable response");
    const reading = readIntent(response);
    const probabilities = Object.fromEntries(reading.ranked.map((r) => [r.label, r.p]));
    outcome = { kind: "answer", label: reading.label, confidence: reading.confidence, probabilities };
    usage = response.usage;
    judge = response.model;
  } catch (e) {
    failed++;
    const kind = e instanceof APIError ? `api ${e.status}` : e instanceof APIConnectionError ? "connection" : "other";
    outcome = { kind: "error", message: `${kind}: ${e instanceof Error ? e.message : String(e)}` };
  }
  const line: RunLine = {
    judge,
    case_id: c.id,
    repeat,
    cold: n === 0,
    started_at: startedAt,
    latency_ms: Math.round(performance.now() - started),
    outcome,
    input_tokens: usage.input_tokens,
    output_tokens: usage.output_tokens,
    cost_usd: costUsd(usage.input_tokens),
    request: built.request,
    raw_response: raw,
  };
  appendFileSync(OUT, `${JSON.stringify(line)}\n`);
  const shown = outcome.kind === "answer" ? `${outcome.label} (${outcome.confidence?.toFixed(2)})` : `ERROR ${outcome.message}`;
  process.stdout.write(`[${n + 1}/${jobs.length}] r${repeat} ${c.id}: ${shown} ${line.latency_ms}ms\n`);
}
process.stdout.write(`done, ${failed} failed → ${OUT}\n`);
process.exit(failed > 0 ? 1 : 0);
