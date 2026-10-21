import type { ApiErrorKind, JevCallErrorKind } from "../core/api-errors.ts";
import { isRecord } from "../core/guards.ts";
import type { IncomingMessage, ServerResponse } from "node:http";
import { parseJevResponse, type JevRequest } from "../core/jev.ts";
import { stationById } from "../core/stations/index.ts";
import { mergeWording } from "../core/wording.ts";

/** Sends a request to Jev. Throws `JevCallError` for API and connection failures. */
export type JevCaller = (request: JevRequest) => Promise<unknown>;

export class JevCallError extends Error {
  override name = "JevCallError";
  readonly kind: JevCallErrorKind;
  constructor(kind: JevCallErrorKind, message: string) {
    super(message);
    this.kind = kind;
  }
}

export type Limits = {
  /** Live requests this process will send before refusing more. */
  readonly maxRequests: number;
  /** Input tokens per UTC day before refusing more. */
  readonly maxDailyTokens: number;
};

export const DEFAULT_LIMITS: Limits = { maxRequests: 500, maxDailyTokens: 2_000_000 };

/** Read limits from `JEVEX_MAX_REQUESTS` and `JEVEX_MAX_DAILY_TOKENS`, falling back to the defaults. */
export function limitsFromEnv(env: Readonly<Record<string, string | undefined>>): Limits {
  const num = (v: string | undefined, fallback: number) => {
    const n = Number(v);
    return v !== undefined && v.trim() !== "" && Number.isFinite(n) && n >= 0 ? n : fallback;
  };
  return {
    maxRequests: num(env.JEVEX_MAX_REQUESTS, DEFAULT_LIMITS.maxRequests),
    maxDailyTokens: num(env.JEVEX_MAX_DAILY_TOKENS, DEFAULT_LIMITS.maxDailyTokens),
  };
}

export type ApiOptions = {
  /** `null` when no API key is configured: live mode is unavailable. */
  readonly call: JevCaller | null;
  readonly model: string;
  readonly limits?: Limits;
  /** Clock for the daily token window; injectable for tests. */
  readonly now?: () => Date;
};

type Next = () => void;
export type ApiHandler = (req: IncomingMessage, res: ServerResponse, next: Next) => void;

const MAX_BODY_BYTES = 64 * 1024;

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(JSON.stringify(body));
}

function fail(res: ServerResponse, status: number, kind: ApiErrorKind, message: string): void {
  send(res, status, { error: { kind, message } });
}

/**
 * An upper bound on a request's input tokens, reserved before the call so concurrent requests
 * cannot push the day past the cap. Measured on this demo's recordings: every request had at
 * least 0.85 characters of state + questions JSON per input token.
 */
export function estimateInputTokens(request: JevRequest): number {
  return Math.ceil(JSON.stringify({ state: request.state, questions: request.questions }).length / 0.85);
}

function logInternalError(path: string, e: unknown): void {
  // One JSON line on stderr, so a 500 can be traced from the server log.
  console.error(
    JSON.stringify({
      event: "api_internal_error",
      path,
      at: new Date().toISOString(),
      message: e instanceof Error ? e.message : String(e),
      stack: e instanceof Error ? e.stack : undefined,
    }),
  );
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk));
    size += buf.length;
    if (size > MAX_BODY_BYTES) throw new Error("Request body too large");
    chunks.push(buf);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

/** Connect-style middleware: serves `/api/*`, passes everything else to `next`. */
export function createApi(options: ApiOptions): ApiHandler {
  const limits = options.limits ?? DEFAULT_LIMITS;
  const now = options.now ?? (() => new Date());
  // `reserved` holds the estimates of calls still in flight; see estimateInputTokens.
  const usage = { requests: 0, tokensToday: 0, reserved: 0, day: "" };
  const rollDay = () => {
    const day = now().toISOString().slice(0, 10);
    if (day !== usage.day) {
      usage.day = day;
      usage.tokensToday = 0;
    }
  };

  /** The cap that refuses the next request, so the page can say so before anyone asks. */
  function blockedBy(): "request_cap" | "token_cap" | null {
    if (usage.requests >= limits.maxRequests) return "request_cap";
    if (usage.tokensToday + usage.reserved >= limits.maxDailyTokens) return "token_cap";
    return null;
  }

  async function handleAsk(req: IncomingMessage, res: ServerResponse): Promise<void> {
    let body: unknown;
    try {
      body = await readJson(req);
    } catch (e) {
      return fail(res, 400, "bad_request", e instanceof Error ? e.message : "Invalid JSON");
    }
    if (!isRecord(body)) return fail(res, 400, "bad_request", "Body must be a JSON object");
    const station = stationById(body.stationId);
    if (!station) return fail(res, 400, "bad_request", "Unknown stationId");
    const wording = mergeWording(station.defaultWording, body.wording);
    if (wording.kind === "error") return fail(res, 400, "bad_request", wording.message);
    const built = station.build({ raw: body.input, wording: wording.wording, model: options.model });
    if (built.kind === "error") {
      return built.reason === "too_long" ? fail(res, 413, "too_long", built.message) : fail(res, 400, "bad_request", built.message);
    }
    if (!options.call) return fail(res, 503, "live_unavailable", "Live mode needs TYPESAFE_API_KEY on the server");
    rollDay();
    if (usage.requests >= limits.maxRequests) {
      return fail(res, 429, "request_cap", `This server has sent its ${limits.maxRequests} live requests; restart it or raise JEVEX_MAX_REQUESTS`);
    }
    const estimate = estimateInputTokens(built.request);
    if (usage.tokensToday + usage.reserved + estimate > limits.maxDailyTokens) {
      return fail(res, 429, "token_cap", `Today's ${limits.maxDailyTokens} input tokens are used; raise JEVEX_MAX_DAILY_TOKENS`);
    }
    // A failed call still counts: it was sent, and the cap exists to bound what this process sends.
    usage.requests++;
    usage.reserved += estimate;

    const started = performance.now();
    let raw: unknown;
    try {
      raw = await options.call(built.request);
    } catch (e) {
      if (e instanceof JevCallError) return fail(res, 502, e.kind, e.message);
      throw e;
    } finally {
      usage.reserved -= estimate;
    }
    const latency_ms = Math.round(performance.now() - started);
    const response = parseJevResponse(raw);
    if (!response) return fail(res, 502, "api_error", "Jev returned a response this demo cannot read");
    // Unknown usage counts as the estimate, so the cap still holds.
    usage.tokensToday += response.usage.input_tokens ?? estimate;
    send(res, 200, { request: built.request, response, latency_ms });
  }

  return (req, res, next) => {
    const path = (req.url ?? "").split("?")[0];
    if (path === "/api/health" && req.method === "GET") {
      rollDay();
      return send(res, 200, {
        live: options.call !== null,
        model: options.model,
        limits,
        usage: { requests: usage.requests, tokensToday: usage.tokensToday },
        blocked: blockedBy(),
      });
    }
    if (path === "/api/ask" && req.method === "POST") {
      handleAsk(req, res).catch((e: unknown) => {
        logInternalError(path, e);
        if (!res.headersSent) fail(res, 500, "internal", e instanceof Error ? e.message : "Internal error");
      });
      return;
    }
    if (path?.startsWith("/api/")) return fail(res, 404, "bad_request", "Unknown API route");
    next();
  };
}
