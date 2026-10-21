import { isApiErrorKind, type ApiErrorKind } from "../core/api-errors.ts";
import { isRecord } from "../core/guards.ts";
import { useCallback, useEffect, useRef, useState } from "react";
import { parseJevRequest, parseJevResponse, type JevRequest, type JevResponse } from "../core/jev.ts";
import { recordingKey } from "../core/recording.ts";
import { MODEL } from "../core/config.ts";
import type { StationDef, StationId } from "../core/stations/station.ts";
import type { Wording } from "../core/wording.ts";
import { useDemo } from "./demo.tsx";
import { recordings } from "./recordings.ts";

export type JevResult =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | {
      readonly kind: "ok";
      readonly source: "recorded" | "live";
      readonly request: JevRequest;
      readonly response: JevResponse;
      readonly latencyMs: number;
      readonly recordedAt: string | null;
    }
  | { readonly kind: "not_recorded"; readonly request: JevRequest }
  | { readonly kind: "error"; readonly errorKind: JevErrorKind; readonly message: string };

/** A server error kind, a local input error, or a status the server sent without a kind. */
export type JevErrorKind = ApiErrorKind | "invalid" | `http_${number}`;

export const CAP_MESSAGES: Readonly<Record<"request_cap" | "token_cap", string>> = {
  request_cap: "This server has sent all its live requests; restart it or raise JEVEX_MAX_REQUESTS",
  token_cap: "Today's input-token budget is used; raise JEVEX_MAX_DAILY_TOKENS",
};

async function askLive(stationId: StationId, raw: unknown, wording: Wording): Promise<JevResult> {
  let res: Response;
  try {
    res = await fetch("api/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stationId, input: raw, wording }),
    });
  } catch (e) {
    return { kind: "error", errorKind: "connection_error", message: e instanceof Error ? e.message : "Network error" };
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const error = isRecord(body) && isRecord(body.error) ? body.error : {};
    return {
      kind: "error",
      errorKind: isApiErrorKind(error.kind) ? error.kind : `http_${res.status}`,
      message: typeof error.message === "string" ? error.message : res.statusText,
    };
  }
  const response = isRecord(body) ? parseJevResponse(body.response) : null;
  const request = isRecord(body) ? parseJevRequest(body.request) : null;
  if (!isRecord(body) || !response || !request) {
    return { kind: "error", errorKind: "api_error", message: "The server sent a response this page cannot read" };
  }
  return {
    kind: "ok",
    source: "live",
    request,
    response,
    latencyMs: typeof body.latency_ms === "number" ? body.latency_ms : 0,
    recordedAt: null,
  };
}

/**
 * Ask Jev through the current mode. Recorded mode builds the request locally with the
 * station's default wording and replays the recording for it; live mode goes to the server.
 */
export type Jev = {
  readonly result: JevResult;
  readonly run: (raw: unknown) => void;
  /** The meaning sent in live mode; recorded mode always replays the default wording. */
  readonly wording: Wording;
  readonly setWording: (w: Wording) => void;
  readonly defaultWording: Wording;
};

export function useJev(station: StationDef): Jev {
  const { mode, liveBlocked, refreshHealth } = useDemo();
  const [result, setResult] = useState<JevResult>({ kind: "idle" });
  const [wording, setWording] = useState<Wording>(station.defaultWording);
  const wordingRef = useRef(wording);
  wordingRef.current = wording;
  const latest = useRef(0);
  useEffect(() => () => void (latest.current = -1), []);

  const run = useCallback(
    (raw: unknown) => {
      const wording = wordingRef.current;
      const id = ++latest.current;
      const settle = (r: JevResult) => {
        if (latest.current === id) setResult(r);
      };
      setResult({ kind: "loading" });
      if (mode === "live") {
        // Say which cap is reached without sending; the server enforces it either way.
        if (liveBlocked) {
          settle({ kind: "error", errorKind: liveBlocked, message: CAP_MESSAGES[liveBlocked] });
          return;
        }
        void askLive(station.id, raw, wording).then((r) => {
          settle(r);
          refreshHealth();
        });
        return;
      }
      const built = station.build({ raw, wording: station.defaultWording, model: MODEL });
      if (built.kind === "error") {
        settle({ kind: "error", errorKind: built.reason, message: built.message });
        return;
      }
      void recordingKey(built.request).then((key) => {
        const rec = recordings.get(key);
        settle(
          rec
            ? { kind: "ok", source: "recorded", request: rec.request, response: rec.response, latencyMs: rec.latency_ms, recordedAt: rec.recorded_at }
            : { kind: "not_recorded", request: built.request },
        );
      });
    },
    [mode, station, liveBlocked, refreshHealth],
  );

  return { result, run, wording, setWording, defaultWording: station.defaultWording };
}
