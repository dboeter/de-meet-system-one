import { INTENTS, type Intent } from "../../src/core/stations/intent.ts";

/** One labelled Intent email from `data/corpus.jsonl`, labelled by `data/rubric.md`. */
export type IntentCase = {
  readonly id: string;
  readonly text: string;
  readonly gold: Intent;
  readonly tags: readonly string[];
  readonly note: string;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isIntent(v: unknown): v is Intent {
  return INTENTS.some((i) => i === v);
}

/**
 * Read the Intent cases from the shared corpus. Lines for other stations are skipped; a
 * malformed Intent line or a duplicate id throws with its line number.
 */
export function parseIntentCases(jsonl: string): IntentCase[] {
  const cases: IntentCase[] = [];
  const seen = new Set<string>();
  for (const [i, line] of jsonl.split("\n").entries()) {
    if (line.trim() === "") continue;
    const v: unknown = JSON.parse(line);
    if (!isRecord(v)) throw new Error(`corpus line ${i + 1}: not an object`);
    if (v.station !== "intent") continue;
    const { id, text, gold, tags, note } = v;
    if (
      typeof id !== "string" ||
      typeof text !== "string" ||
      text.trim() === "" ||
      !isIntent(gold) ||
      !Array.isArray(tags) ||
      !tags.every((t) => typeof t === "string") ||
      typeof note !== "string"
    ) {
      throw new Error(`corpus line ${i + 1}: expected {station, id, text, gold, tags, note}`);
    }
    if (seen.has(id)) throw new Error(`corpus line ${i + 1}: duplicate id "${id}"`);
    seen.add(id);
    cases.push({ id, text, gold, tags, note });
  }
  return cases;
}
