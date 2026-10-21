/**
 * One judge call on one corpus case, as written to `data/runs/<judge>.jsonl`. The shape is
 * judge-agnostic so a Haiku run written in the same format is scored by the same report.
 */
export type Outcome =
  | {
      readonly kind: "answer";
      readonly label: string;
      /** The judge's own confidence, or `null` when it reports none. */
      readonly confidence: number | null;
      /** Probability per option, or `null` when the judge returns only a label. */
      readonly probabilities: Readonly<Record<string, number>> | null;
    }
  | { readonly kind: "error"; readonly message: string };

export type RunLine = {
  /** The model ID as returned by the API, e.g. `jev-1.13.0`. */
  readonly judge: string;
  readonly case_id: string;
  readonly repeat: number;
  /** First call of the process: connection setup is included in its latency. */
  readonly cold: boolean;
  readonly started_at: string;
  /** Wall clock around one attempt, retries disabled. */
  readonly latency_ms: number;
  readonly outcome: Outcome;
  readonly input_tokens: number | null;
  readonly output_tokens: number | null;
  readonly cost_usd: number | null;
  /** The exact request sent, so another judge can be given the same question. */
  readonly request: unknown;
  readonly raw_response: unknown;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const numOrNull = (v: unknown): v is number | null => v === null || typeof v === "number";

function isNumberRecord(v: unknown): v is Record<string, number> {
  return isRecord(v) && Object.values(v).every((x) => typeof x === "number");
}

function parseOutcome(v: unknown): Outcome | null {
  if (!isRecord(v)) return null;
  if (v.kind === "error") return typeof v.message === "string" ? { kind: "error", message: v.message } : null;
  if (v.kind !== "answer" || typeof v.label !== "string" || !numOrNull(v.confidence)) return null;
  if (v.probabilities !== null && !isNumberRecord(v.probabilities)) return null;
  return { kind: "answer", label: v.label, confidence: v.confidence, probabilities: v.probabilities };
}

function parseRunLine(v: unknown): RunLine | null {
  if (!isRecord(v)) return null;
  const outcome = parseOutcome(v.outcome);
  const { judge, case_id, repeat, cold, started_at, latency_ms, input_tokens, output_tokens, cost_usd } = v;
  if (
    !outcome ||
    typeof judge !== "string" ||
    typeof case_id !== "string" ||
    typeof repeat !== "number" ||
    typeof cold !== "boolean" ||
    typeof started_at !== "string" ||
    typeof latency_ms !== "number" ||
    !numOrNull(input_tokens) ||
    !numOrNull(output_tokens) ||
    !numOrNull(cost_usd)
  ) {
    return null;
  }
  return {
    judge,
    case_id,
    repeat,
    cold,
    started_at,
    latency_ms,
    outcome,
    input_tokens,
    output_tokens,
    cost_usd,
    request: v.request,
    raw_response: v.raw_response,
  };
}

export function parseRunLines(jsonl: string): RunLine[] {
  const out: RunLine[] = [];
  for (const [i, line] of jsonl.split("\n").entries()) {
    if (line.trim() === "") continue;
    let parsed: RunLine | null;
    try {
      parsed = parseRunLine(JSON.parse(line));
    } catch {
      parsed = null;
    }
    if (!parsed) throw new Error(`Malformed run line ${i + 1}`);
    out.push(parsed);
  }
  return out;
}
