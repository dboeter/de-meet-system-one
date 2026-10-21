import { isRecord } from "./guards.ts";
import { parseJevRequest, parseJevResponse, type JevRequest, type JevResponse } from "./jev.ts";

/**
 * One recorded Jev call. `repeat` is 0 for the answer the demo replays; higher values are
 * extra calls with the identical request, kept to measure repeat noise.
 */
export type Recording = {
  readonly key: string;
  readonly repeat: number;
  readonly model: string;
  readonly request: JevRequest;
  readonly response: JevResponse;
  readonly latency_ms: number;
  readonly recorded_at: string;
};

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((k) => [k, canonicalize((value as Record<string, unknown>)[k])]),
    );
  }
  return value;
}

/** JSON with object keys sorted at every depth, so equal requests serialise identically. */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalize(value));
}

/** SHA-256 hex of the canonical `{model, state, questions}`. Works in Node and the browser. */
export async function recordingKey(request: JevRequest): Promise<string> {
  const body = canonicalJson({ model: request.model, state: request.state, questions: request.questions });
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function parseRecording(v: unknown): Recording | null {
  if (!isRecord(v)) return null;
  const request = parseJevRequest(v.request);
  const response = parseJevResponse(v.response);
  if (
    typeof v.key !== "string" ||
    typeof v.repeat !== "number" ||
    typeof v.model !== "string" ||
    typeof v.latency_ms !== "number" ||
    typeof v.recorded_at !== "string" ||
    !request ||
    !response
  ) {
    return null;
  }
  return {
    key: v.key,
    repeat: v.repeat,
    model: v.model,
    request,
    response,
    latency_ms: v.latency_ms,
    recorded_at: v.recorded_at,
  };
}

export function parseRecordings(jsonl: string): Recording[] {
  const out: Recording[] = [];
  for (const [i, line] of jsonl.split("\n").entries()) {
    if (line.trim() === "") continue;
    let parsed: Recording | null = null;
    try {
      parsed = parseRecording(JSON.parse(line));
    } catch {
      parsed = null;
    }
    if (!parsed) throw new Error(`Malformed recording on line ${i + 1}`);
    out.push(parsed);
  }
  return out;
}

export class RecordingStore {
  readonly #byKey = new Map<string, Recording[]>();
  readonly #order: Recording[] = [];

  constructor(recordings: readonly Recording[]) {
    for (const r of recordings) this.add(r);
  }

  add(recording: Recording): void {
    const list = this.#byKey.get(recording.key) ?? [];
    list.push(recording);
    this.#byKey.set(recording.key, list);
    this.#order.push(recording);
  }

  get(key: string, repeat = 0): Recording | undefined {
    return this.#byKey.get(key)?.find((r) => r.repeat === repeat);
  }

  repeats(key: string): readonly Recording[] {
    return this.#byKey.get(key) ?? [];
  }

  get size(): number {
    return this.#order.length;
  }

  /** Every line in insertion order, so appending keeps diffs small. */
  toJsonl(): string {
    return this.#order.map((r) => `${JSON.stringify(r)}\n`).join("");
  }
}
