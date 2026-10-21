/** A plain JSON object, as opposed to an array or null. For validating data that crossed a boundary. */
export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
