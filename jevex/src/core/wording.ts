/**
 * The editable meaning of a station: per wording key, the question text and the
 * descriptions of its options. Option names stay fixed; only their descriptions can change.
 */

import { isRecord } from "./guards.ts";
export type WordingEntry = {
  readonly instructions: string;
  readonly criteria?: Readonly<Record<string, string | null>>;
};
export type Wording = Readonly<Record<string, WordingEntry>>;

export const MAX_INSTRUCTIONS_CHARS = 1000;
export const MAX_DESCRIPTION_CHARS = 500;

/**
 * Overlay viewer edits onto the station defaults. Unknown keys and options are dropped and
 * over-long text is rejected, so a client cannot turn the server into a generic proxy.
 */
export function mergeWording(
  defaults: Wording,
  raw: unknown,
): { readonly kind: "ok"; readonly wording: Wording } | { readonly kind: "error"; readonly message: string } {
  if (raw === undefined || raw === null) return { kind: "ok", wording: defaults };
  if (!isRecord(raw)) return { kind: "error", message: "wording must be an object" };
  const out: Record<string, WordingEntry> = {};
  for (const [key, base] of Object.entries(defaults)) {
    const edit = raw[key];
    if (edit === undefined) {
      out[key] = base;
      continue;
    }
    if (!isRecord(edit)) return { kind: "error", message: `wording.${key} must be an object` };
    const instructions = edit.instructions ?? base.instructions;
    if (typeof instructions !== "string" || instructions.trim() === "" || instructions.length > MAX_INSTRUCTIONS_CHARS) {
      return { kind: "error", message: `wording.${key}.instructions must be 1–${MAX_INSTRUCTIONS_CHARS} characters` };
    }
    let criteria = base.criteria;
    if (base.criteria && isRecord(edit.criteria)) {
      const merged: Record<string, string | null> = { ...base.criteria };
      for (const option of Object.keys(base.criteria)) {
        const d = edit.criteria[option];
        if (d === undefined) continue;
        if (d !== null && (typeof d !== "string" || d.length > MAX_DESCRIPTION_CHARS)) {
          return { kind: "error", message: `wording.${key}.criteria.${option} must be text up to ${MAX_DESCRIPTION_CHARS} characters` };
        }
        merged[option] = d === "" ? null : d;
      }
      criteria = merged;
    }
    out[key] = criteria ? { instructions, criteria } : { instructions };
  }
  return { kind: "ok", wording: out };
}

/** The entry for `key`, or the station default when the wording lacks it (mergeWording keeps every default key). */
export function wordingEntry<K extends string>(wording: Wording, defaults: Readonly<Record<K, WordingEntry>>, key: K): WordingEntry {
  return wording[key] ?? defaults[key];
}
