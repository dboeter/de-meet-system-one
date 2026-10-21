/**
 * Production server: serves the built app from `dist/` and the live API from `/api`.
 * Reads `TYPESAFE_API_KEY` from the environment or a `.env` file in the working directory.
 */
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";
import { MODEL } from "../core/config.ts";
import { createApi, limitsFromEnv } from "./api.ts";
import { createJevCaller } from "./jev-client.ts";

if (existsSync(".env")) process.loadEnvFile();

const DIST = resolve("dist");
const PORT = Number(process.env.PORT ?? 8787);
const TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".jsonl": "application/x-ndjson",
};

const api = createApi({ call: createJevCaller(process.env.TYPESAFE_API_KEY), model: MODEL, limits: limitsFromEnv(process.env) });

const server = createServer((req, res) => {
  api(req, res, () => {
    const urlPath = decodeURIComponent((req.url ?? "/").split("?")[0] ?? "/");
    const candidate = normalize(join(DIST, urlPath));
    const file =
      candidate.startsWith(DIST) && existsSync(candidate) && statSync(candidate).isFile() ? candidate : join(DIST, "index.html");
    if (!existsSync(file)) {
      res.writeHead(500).end("dist/ is missing: run `npm run build` first");
      return;
    }
    res.writeHead(200, { "content-type": TYPES[extname(file)] ?? "application/octet-stream" });
    createReadStream(file).pipe(res);
  });
});

server.listen(PORT, () => {
  process.stdout.write(`jevex on http://localhost:${PORT} (live: ${process.env.TYPESAFE_API_KEY ? "on" : "off"}, model ${MODEL})\n`);
});
