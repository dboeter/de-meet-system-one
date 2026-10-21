/**
 * Record Jev answers for every target that lacks one, appending to the recordings file.
 * Usage: npm run record [-- --dry-run]
 * Already-recorded (key, repeat) pairs are skipped, so only new questions cost anything.
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { MODEL } from "../src/core/config.ts";
import { parseJevResponse } from "../src/core/jev.ts";
import { parseRecordings, recordingKey, RecordingStore, type Recording } from "../src/core/recording.ts";
import { allTargets } from "../src/core/all-targets.ts";
import { parseCorpus } from "../src/core/eval.ts";
import { createJevCaller } from "../src/server/jev-client.ts";

const FILE = "src/recordings/recordings.jsonl";
const CORPUS = "data/corpus.jsonl";
const CONCURRENCY = 4;

if (existsSync(".env")) process.loadEnvFile();
const dryRun = process.argv.includes("--dry-run");

const store = new RecordingStore(existsSync(FILE) ? parseRecordings(readFileSync(FILE, "utf8")) : []);

type Job = { label: string; key: string; repeat: number; request: Recording["request"] };
const jobs: Job[] = [];
const corpus = existsSync(CORPUS) ? parseCorpus(readFileSync(CORPUS, "utf8")) : [];
for (const target of allTargets(MODEL, corpus)) {
  const key = await recordingKey(target.request);
  for (let repeat = 0; repeat < target.repeats; repeat++) {
    if (!store.get(key, repeat)) jobs.push({ label: target.label, key, repeat, request: target.request });
  }
}

process.stdout.write(`${jobs.length} recording(s) missing for ${MODEL}\n`);
if (dryRun || jobs.length === 0) process.exit(0);

const call = createJevCaller(process.env.TYPESAFE_API_KEY);
if (!call) {
  process.stderr.write("TYPESAFE_API_KEY is not set\n");
  process.exit(1);
}

let done = 0;
let failed = 0;
async function worker(queue: Job[], caller: NonNullable<typeof call>): Promise<void> {
  for (let job = queue.shift(); job; job = queue.shift()) {
    const started = performance.now();
    try {
      const response = parseJevResponse(await caller(job.request));
      if (!response) throw new Error("unreadable response");
      store.add({
        key: job.key,
        repeat: job.repeat,
        model: response.model,
        request: job.request,
        response,
        latency_ms: Math.round(performance.now() - started),
        recorded_at: new Date().toISOString(),
      });
      done++;
    } catch (e) {
      failed++;
      process.stderr.write(`FAILED ${job.label} (repeat ${job.repeat}): ${e instanceof Error ? e.message : String(e)}\n`);
    }
  }
}

const queue = [...jobs];
await Promise.all(Array.from({ length: CONCURRENCY }, () => worker(queue, call)));
writeFileSync(FILE, store.toJsonl());
process.stdout.write(`recorded ${done}, failed ${failed}, total ${store.size}\n`);
process.exit(failed > 0 ? 1 : 0);
