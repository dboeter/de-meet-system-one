/**
 * The one pinned model for recordings and live calls. A versioned ID, not an alias, so
 * recorded answers and thresholds stay tied to the model that produced them.
 */
export const MODEL = "jev-1.13.0";

/** USD per input token: $0.042 per million (docs.typesafe.ai/models). Output tokens are free. */
export const USD_PER_INPUT_TOKEN = 0.042 / 1_000_000;

export function costUsd(inputTokens: number | null): number | null {
  return inputTokens === null ? null : inputTokens * USD_PER_INPUT_TOKEN;
}

export const MAX_INPUT_CHARS = 4000;
