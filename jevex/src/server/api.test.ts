import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, it } from "vitest";
import type { JevRequest } from "../core/jev.ts";
import { intent } from "../core/stations/intent.ts";
import { createApi, estimateInputTokens, JevCallError, type ApiOptions } from "./api.ts";

const okResponse = {
  model: "jev-1.13.0",
  answers: { intent: { type: "choice", choice: "refund", confidence: 0.9, probabilities: { refund: 0.95, other: 0.05 } } },
  usage: { input_tokens: 400, output_tokens: 30 },
};

let server: Server | undefined;
afterEach(() => server?.close());

async function start(options: Partial<ApiOptions>): Promise<string> {
  const api = createApi({ call: null, model: "jev-1.13.0", ...options });
  server = createServer((req, res) => api(req, res, () => res.writeHead(404).end()));
  await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}

function ask(base: string, body: unknown): Promise<Response> {
  return fetch(`${base}/api/ask`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

describe("GET /api/health", () => {
  it("reports live unavailable without a client", async () => {
    const base = await start({});
    expect(await (await fetch(`${base}/api/health`)).json()).toMatchObject({ live: false, model: "jev-1.13.0" });
  });
});

describe("POST /api/ask", () => {
  it("builds the request from the station module and returns Jev's answer", async () => {
    const sent: JevRequest[] = [];
    const base = await start({
      call: async (r) => {
        sent.push(r);
        return okResponse;
      },
    });
    const res = await ask(base, { stationId: "intent", input: { text: "give me my money back" } });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.response).toEqual(okResponse);
    expect(body.request).toEqual(sent[0]);
    expect(sent[0]?.model).toBe("jev-1.13.0");
    expect(sent[0]?.state).toBe("give me my money back");
    expect(typeof body.latency_ms).toBe("number");
  });

  it("returns 503 live_unavailable when there is no API key", async () => {
    const base = await start({});
    const res = await ask(base, { stationId: "intent", input: { text: "hi" } });
    expect(res.status).toBe(503);
    expect((await res.json()).error.kind).toBe("live_unavailable");
  });

  it("returns 400 for an unknown station or bad input", async () => {
    const base = await start({ call: async () => okResponse });
    expect((await ask(base, { stationId: "nope", input: { text: "hi" } })).status).toBe(400);
    expect((await ask(base, { stationId: "intent", input: {} })).status).toBe(400);
  });

  it("maps an API failure to a typed 502 error", async () => {
    const base = await start({
      call: async () => {
        throw new JevCallError("api_error", "401 Unauthorized");
      },
    });
    const res = await ask(base, { stationId: "intent", input: { text: "hi" } });
    expect(res.status).toBe(502);
    expect((await res.json()).error).toEqual({ kind: "api_error", message: "401 Unauthorized" });
  });

  it("sends edited wording for known keys and ignores unknown ones", async () => {
    const sent: JevRequest[] = [];
    const base = await start({
      call: async (r) => {
        sent.push(r);
        return okResponse;
      },
    });
    const res = await ask(base, {
      stationId: "intent",
      input: { text: "hi" },
      wording: { intent: { instructions: "What is the customer after?", criteria: { refund: "Money back", invented: "x" } }, other: { instructions: "y" } },
    });
    expect(res.status).toBe(200);
    const q = sent[0]?.questions.intent;
    if (q?.type !== "choice") throw new Error("expected choice");
    expect(q.instructions).toBe("What is the customer after?");
    expect(q.criteria.refund).toBe("Money back");
    expect(q.criteria.exchange).toBe("Wants a replacement, a repair or a different item, not money back");
    expect(Object.keys(q.criteria)).not.toContain("invented");
    expect(Object.keys(sent[0]?.questions ?? {})).toEqual(["intent"]);
  });

  it("rejects over-long text with too_long and does not call Jev", async () => {
    let calls = 0;
    const base = await start({
      call: async () => {
        calls++;
        return okResponse;
      },
    });
    const res = await ask(base, { stationId: "intent", input: { text: "x".repeat(4001) } });
    expect(res.status).toBe(413);
    expect((await res.json()).error.kind).toBe("too_long");
    expect(calls).toBe(0);
  });

  it("stops at the per-process request cap", async () => {
    const base = await start({ call: async () => okResponse, limits: { maxRequests: 2, maxDailyTokens: 1_000_000 } });
    expect((await ask(base, { stationId: "intent", input: { text: "a" } })).status).toBe(200);
    expect((await ask(base, { stationId: "intent", input: { text: "b" } })).status).toBe(200);
    const third = await ask(base, { stationId: "intent", input: { text: "c" } });
    expect(third.status).toBe(429);
    expect((await third.json()).error.kind).toBe("request_cap");
  });

  it("refuses a request whose token estimate would pass the day's cap, before calling Jev", async () => {
    const built = intent.build({ raw: { text: "a" }, wording: intent.defaultWording, model: "jev-1.13.0" });
    if (built.kind !== "ok") throw new Error(built.message);
    const estimate = estimateInputTokens(built.request);
    let calls = 0;
    // Room for one estimate, but not for a second after the first used 400 real tokens.
    const cap = estimate + 399;
    const base = await start({ call: async () => (calls++, okResponse), limits: { maxRequests: 100, maxDailyTokens: cap } });
    expect((await ask(base, { stationId: "intent", input: { text: "a" } })).status).toBe(200);
    const second = await ask(base, { stationId: "intent", input: { text: "b" } });
    expect(second.status).toBe(429);
    expect((await second.json()).error.kind).toBe("token_cap");
    expect(calls).toBe(1);
    expect(await (await fetch(`${base}/api/health`)).json()).toMatchObject({ usage: { requests: 1, tokensToday: 400 }, blocked: null });
  });

  it("reports on /api/health which cap blocks the next request", async () => {
    const base = await start({ call: async () => okResponse, limits: { maxRequests: 1, maxDailyTokens: 1_000_000 } });
    await ask(base, { stationId: "intent", input: { text: "a" } });
    expect(await (await fetch(`${base}/api/health`)).json()).toMatchObject({ blocked: "request_cap" });
  });

  it("rejects a response that is not a valid Jev response", async () => {
    const base = await start({ call: async () => ({ nope: true }) });
    const res = await ask(base, { stationId: "intent", input: { text: "hi" } });
    expect(res.status).toBe(502);
    expect((await res.json()).error.kind).toBe("api_error");
  });
});
