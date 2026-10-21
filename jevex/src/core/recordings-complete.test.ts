import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { allTargets } from "./all-targets.ts";
import { MODEL } from "./config.ts";
import { parseCorpus } from "./eval.ts";
import { parseRecordings, recordingKey, RecordingStore } from "./recording.ts";

const CORPUS = "data/corpus.jsonl";

describe("recordings", () => {
  it(`cover every preset and corpus item for ${MODEL}`, async () => {
    const store = new RecordingStore(parseRecordings(readFileSync("src/recordings/recordings.jsonl", "utf8")));
    const corpus = existsSync(CORPUS) ? parseCorpus(readFileSync(CORPUS, "utf8")) : [];
    const missing: string[] = [];
    for (const target of allTargets(MODEL, corpus)) {
      const key = await recordingKey(target.request);
      for (let repeat = 0; repeat < target.repeats; repeat++) {
        if (!store.get(key, repeat)) missing.push(`${target.label} (repeat ${repeat})`);
      }
    }
    expect(missing, "run `npm run record`").toEqual([]);
  });
});
