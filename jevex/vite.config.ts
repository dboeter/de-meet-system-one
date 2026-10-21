import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";
import { MODEL } from "./src/core/config.ts";
import { createApi, limitsFromEnv } from "./src/server/api.ts";
import { createJevCaller } from "./src/server/jev-client.ts";

/** Mounts the live API on the dev and preview servers, so `npm run dev` is one process. */
function jevApi(env: Record<string, string>): Plugin {
  const api = createApi({ call: createJevCaller(env.TYPESAFE_API_KEY), model: MODEL, limits: limitsFromEnv(env) });
  return {
    name: "jevex-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => api(req, res, next));
    },
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => api(req, res, next));
    },
  };
}

export default defineConfig(({ mode }) => {
  // Empty prefix: read TYPESAFE_API_KEY too. It stays in this Node process, never in the bundle.
  const env = loadEnv(mode, process.cwd(), "");
  return {
    // Relative asset paths so the recorded-only build works from any static host subpath.
    base: "./",
    plugins: [react(), jevApi(env)],
  };
});
