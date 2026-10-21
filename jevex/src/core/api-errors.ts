/** Error kinds the live API returns in `{error: {kind, message}}`. Shared by server and browser. */
export const API_ERROR_KINDS = [
  "bad_request",
  "too_long",
  "live_unavailable",
  "request_cap",
  "token_cap",
  "api_error",
  "connection_error",
  "internal",
] as const;
export type ApiErrorKind = (typeof API_ERROR_KINDS)[number];

/** The subset a failed call to Jev itself produces. */
export type JevCallErrorKind = Extract<ApiErrorKind, "api_error" | "connection_error">;

export function isApiErrorKind(v: unknown): v is ApiErrorKind {
  return typeof v === "string" && (API_ERROR_KINDS as readonly string[]).includes(v);
}
